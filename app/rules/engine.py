"""
RulesEngine: scans symbols in enabled rules, evaluates candidates, returns trade candidates.
"""
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.position import OptionPosition
from app.models.rule import SellPutRule
from app.rules.evaluators import (
    check_daily_drop,
    check_delta,
    check_dte,
    check_iv_rank,
    check_otm,
    check_otm_call,
    check_otm_put,
    check_premium_pct,
    score_candidate,
)
from app.schwab.iv_rank import iv_rank_tracker
from app.schwab.option_chain import OptionCandidate, parse_option_chain

logger = structlog.get_logger(__name__)


@dataclass
class TradeCandidate:
    rule: SellPutRule
    candidate: OptionCandidate
    contracts: int
    symbol: str


class RulesEngine:
    async def scan_all_enabled_rules(
        self, db: AsyncSession, schwab_client: Any
    ) -> list[TradeCandidate]:
        result = await db.execute(select(SellPutRule).where(SellPutRule.enabled == True))
        rules = result.scalars().all()

        all_candidates: list[TradeCandidate] = []
        for rule in rules:
            try:
                candidates = await self.evaluate_rule(rule, db, schwab_client)
                all_candidates.extend(candidates)
            except Exception as exc:
                logger.error("Rule evaluation failed", rule_id=rule.id, rule_name=rule.name, error=str(exc))

        return all_candidates

    async def evaluate_rule(
        self, rule: SellPutRule, db: AsyncSession, schwab_client: Any
    ) -> list[TradeCandidate]:
        from datetime import datetime
        strategy_type = getattr(rule, 'strategy_type', 'SELL_PUT') or 'SELL_PUT'
        symbols_sorted = sorted(rule.symbols or [], key=lambda s: s.get("priority", 99))
        symbol_names = [s["symbol"] for s in symbols_sorted]
        if not symbol_names:
            return []

        quotes = await schwab_client.get_quotes(symbol_names)

        # Count OPEN + CLOSING positions (don't open new while a close order is in flight)
        open_count_result = await db.execute(
            select(func.count(OptionPosition.id)).where(
                OptionPosition.rule_id == rule.id,
                OptionPosition.status.in_(["OPEN", "CLOSING"]),
            )
        )
        open_count = open_count_result.scalar() or 0

        account = await schwab_client.get_account()

        shares_by_symbol: dict[str, int] = {}
        if strategy_type == "SELL_COVERED_CALL":
            positions_list = account.get("securitiesAccount", {}).get("positions", [])
            for pos in positions_list:
                inst = pos.get("instrument", {})
                if inst.get("assetType") == "EQUITY":
                    shares_by_symbol[inst.get("symbol", "")] = int(pos.get("longQuantity", 0))

        buying_power = float(
            account.get("securitiesAccount", {})
            .get("currentBalances", {})
            .get("buyingPower", 0)
        )

        results: list[TradeCandidate] = []
        contract_type = "CALL" if strategy_type == "SELL_COVERED_CALL" else "PUT"

        # Collect per-symbol notes; last one wins for the rule's scan note
        symbol_notes: list[str] = []

        for sym_entry in symbols_sorted:
            symbol = sym_entry["symbol"]

            if open_count >= rule.max_open_positions:
                symbol_notes.append(f"{symbol}: max {rule.max_open_positions} position(s) already open")
                logger.info("Max open positions reached for rule", rule_id=rule.id, open_count=open_count)
                break

            quote_data = quotes.get(symbol, {}).get("quote", {})
            current_price = float(quote_data.get("lastPrice") or quote_data.get("mark") or 0)
            open_price = float(quote_data.get("openPrice") or current_price)

            if current_price <= 0:
                symbol_notes.append(f"{symbol}: no live quote available")
                logger.warning("No quote for symbol", symbol=symbol)
                continue

            # Daily drop filter
            if not check_daily_drop(current_price, open_price, rule.min_daily_drop_pct, rule.max_daily_drop_pct):
                if open_price > 0:
                    drop_pct = (open_price - current_price) / open_price * 100
                    if rule.min_daily_drop_pct and drop_pct < rule.min_daily_drop_pct:
                        symbol_notes.append(
                            f"{symbol}: down {drop_pct:.1f}% today, need ≥{rule.min_daily_drop_pct}%"
                        )
                    else:
                        symbol_notes.append(f"{symbol}: daily move {drop_pct:.1f}% outside filter range")
                continue

            # Already have OPEN or CLOSING position for this symbol
            existing = await db.execute(
                select(OptionPosition).where(
                    OptionPosition.rule_id == rule.id,
                    OptionPosition.underlying_symbol == symbol,
                    OptionPosition.status.in_(["OPEN", "CLOSING"]),
                )
            )
            if existing.scalar_one_or_none():
                symbol_notes.append(f"{symbol}: already have an open/closing position")
                logger.debug("Skipping symbol — already have open/closing position", symbol=symbol, rule_id=rule.id)
                continue

            shares_owned = 0
            if strategy_type == "SELL_COVERED_CALL":
                shares_owned = shares_by_symbol.get(symbol, 0)
                if shares_owned < 100:
                    symbol_notes.append(f"{symbol}: need ≥100 shares for covered call (have {shares_owned})")
                    continue

            raw_chain = await schwab_client.get_option_chain(
                symbol, min_dte=rule.min_dte, max_dte=rule.max_dte, contract_type=contract_type
            )
            iv_rank = iv_rank_tracker.get_iv_rank(symbol)
            candidates = parse_option_chain(raw_chain, iv_rank=iv_rank, contract_type=contract_type)

            min_premium_mode = getattr(rule, 'min_premium_mode', 'pct') or 'pct'
            min_premium_dollar_val = getattr(rule, 'min_premium_dollar', None)
            strike_min = getattr(rule, 'strike_min', None)
            strike_max = getattr(rule, 'strike_max', None)
            max_premium_dollar_val = getattr(rule, 'max_premium_dollar', None)
            min_iv_pct = getattr(rule, 'min_iv_pct', None)
            max_iv_pct = getattr(rule, 'max_iv_pct', None)

            # Filter + track best available premium for diagnostics
            passing = []
            best_mid_in_dte = 0.0  # best mid among options that passed DTE + OTM filters
            dte_matched = 0

            for c in candidates:
                if not check_dte(c, rule.min_dte, rule.max_dte):
                    continue
                if strategy_type == "SELL_COVERED_CALL":
                    if not check_otm_call(c):
                        continue
                else:
                    if not check_otm_put(c):
                        continue
                dte_matched += 1
                if c.mid > best_mid_in_dte:
                    best_mid_in_dte = c.mid
                if strike_min is not None and c.strike < strike_min:
                    continue
                if strike_max is not None and c.strike > strike_max:
                    continue
                if min_premium_mode == 'dollar' and min_premium_dollar_val is not None:
                    if c.mid < min_premium_dollar_val:
                        continue
                    if max_premium_dollar_val is not None and c.mid > max_premium_dollar_val:
                        continue
                else:
                    if not check_premium_pct(c, rule.min_premium_pct, rule.max_premium_pct):
                        continue
                if min_iv_pct is not None and c.iv < min_iv_pct:
                    continue
                if max_iv_pct is not None and c.iv > max_iv_pct:
                    continue
                if not check_delta(c, rule.min_delta, rule.max_delta):
                    continue
                if not check_iv_rank(c, rule.min_iv_rank):
                    continue
                passing.append(c)

            if not passing:
                if dte_matched == 0:
                    symbol_notes.append(
                        f"{symbol}: no options found in {rule.min_dte}–{rule.max_dte} DTE range"
                    )
                else:
                    # Options exist but premium filter (or other) blocked them
                    if min_premium_mode == 'dollar' and min_premium_dollar_val is not None:
                        req_str = f"≥${min_premium_dollar_val:.2f}"
                    else:
                        req_dollar = current_price * rule.min_premium_pct / 100
                        req_str = f"≥{rule.min_premium_pct}% (≥${req_dollar:.2f})"
                    symbol_notes.append(
                        f"{symbol}: best premium ${best_mid_in_dte:.2f} — need {req_str}"
                    )
                logger.info("No qualifying options found", symbol=symbol, rule_id=rule.id)
                continue

            best = max(passing, key=lambda c: score_candidate(c, strategy_type))

            position_size_mode = getattr(rule, 'position_size_mode', 'pct') or 'pct'
            position_size_contracts_val = getattr(rule, 'position_size_contracts', None)

            if strategy_type == "SELL_COVERED_CALL":
                max_by_shares = shares_owned // 100
                if position_size_mode == 'contracts' and position_size_contracts_val:
                    contracts = min(position_size_contracts_val, max_by_shares)
                else:
                    contracts = max_by_shares
                if rule.max_position_size_usd:
                    contracts = min(contracts, int(rule.max_position_size_usd / (best.strike * 100)))
                if contracts < 1:
                    symbol_notes.append(f"{symbol}: not enough shares after sizing (have {shares_owned})")
                    continue
            else:
                contracts = _calculate_contracts(best.strike, buying_power, rule, position_size_mode, position_size_contracts_val)
                if contracts < 1:
                    required = best.strike * 100
                    symbol_notes.append(
                        f"{symbol}: need ${required:,.0f} per contract, have ${buying_power:,.0f} buying power"
                    )
                    logger.info(
                        "Insufficient buying power for sell put",
                        symbol=symbol,
                        strike=best.strike,
                        required_per_contract=required,
                        available_buying_power=round(buying_power, 2),
                    )
                    continue

            symbol_notes.append(
                f"✓ {symbol}: queued {contracts}x ${best.strike}{'C' if contract_type == 'CALL' else 'P'} @ ${best.mid:.2f}"
            )
            results.append(TradeCandidate(rule=rule, candidate=best, contracts=contracts, symbol=symbol))
            open_count += 1

        # Save scan note to the rule
        note = " | ".join(symbol_notes) if symbol_notes else "Scan ran — no symbols to evaluate"
        try:
            rule_row = await db.get(SellPutRule, rule.id)
            if rule_row:
                rule_row.last_scan_note = note[:500]
                rule_row.last_scanned_at = datetime.utcnow()
                await db.commit()
        except Exception as exc:
            logger.warning("Could not save scan note", rule_id=rule.id, error=str(exc))

        return results


def _calculate_contracts(
    strike: float,
    buying_power: float,
    rule: SellPutRule,
    position_size_mode: str = "pct",
    position_size_contracts_val: int | None = None,
) -> int:
    """Calculate number of contracts based on position sizing rules."""
    if position_size_mode == 'contracts' and position_size_contracts_val:
        contracts = position_size_contracts_val
    else:
        allocated = buying_power * rule.position_size_pct
        if rule.max_position_size_usd:
            allocated = min(allocated, rule.max_position_size_usd)
        contracts = int(allocated / (strike * 100))
    return max(0, contracts)


# Singleton
rules_engine = RulesEngine()
