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
        # Determine strategy type
        strategy_type = getattr(rule, 'strategy_type', 'SELL_PUT') or 'SELL_PUT'

        # Sort symbols by priority (lower number = higher priority)
        symbols_sorted = sorted(rule.symbols or [], key=lambda s: s.get("priority", 99))

        # Get live quotes for all symbols in one call
        symbol_names = [s["symbol"] for s in symbols_sorted]
        if not symbol_names:
            return []

        quotes = await schwab_client.get_quotes(symbol_names)

        # Check open position count for this rule
        open_count_result = await db.execute(
            select(func.count(OptionPosition.id)).where(
                OptionPosition.rule_id == rule.id,
                OptionPosition.status == "OPEN",
            )
        )
        open_count = open_count_result.scalar() or 0

        # Get account data
        account = await schwab_client.get_account()

        # For covered calls: build shares-by-symbol map from account positions
        shares_by_symbol: dict[str, int] = {}
        if strategy_type == "SELL_COVERED_CALL":
            positions_list = account.get("securitiesAccount", {}).get("positions", [])
            for pos in positions_list:
                inst = pos.get("instrument", {})
                if inst.get("assetType") == "EQUITY":
                    shares_by_symbol[inst.get("symbol", "")] = int(pos.get("longQuantity", 0))

        # For sell puts: get buying power
        buying_power = float(
            account.get("securitiesAccount", {})
            .get("currentBalances", {})
            .get("buyingPower", 0)
        )

        results: list[TradeCandidate] = []

        # Determine contract type for option chain fetch
        contract_type = "CALL" if strategy_type == "SELL_COVERED_CALL" else "PUT"

        for sym_entry in symbols_sorted:
            symbol = sym_entry["symbol"]

            if open_count >= rule.max_open_positions:
                logger.info("Max open positions reached for rule", rule_id=rule.id, open_count=open_count)
                break

            quote_data = quotes.get(symbol, {}).get("quote", {})
            current_price = float(quote_data.get("lastPrice") or quote_data.get("mark") or 0)
            open_price = float(quote_data.get("openPrice") or current_price)

            if current_price <= 0:
                logger.warning("No quote for symbol", symbol=symbol)
                continue

            # Apply daily drop filter (only relevant for SELL_PUT; covered calls skip it unless set)
            if not check_daily_drop(current_price, open_price, rule.min_daily_drop_pct, rule.max_daily_drop_pct):
                logger.debug(
                    "Symbol skipped — daily drop filter not met",
                    symbol=symbol,
                    current_price=current_price,
                    open_price=open_price,
                    min_drop_pct=rule.min_daily_drop_pct,
                )
                continue

            # Check if we already have an open position for this symbol under this rule
            existing = await db.execute(
                select(OptionPosition).where(
                    OptionPosition.rule_id == rule.id,
                    OptionPosition.underlying_symbol == symbol,
                    OptionPosition.status == "OPEN",
                )
            )
            if existing.scalar_one_or_none():
                logger.debug("Skipping symbol — already have open position", symbol=symbol, rule_id=rule.id)
                continue

            # For covered calls: check shares owned before fetching the chain
            shares_owned = 0
            if strategy_type == "SELL_COVERED_CALL":
                shares_owned = shares_by_symbol.get(symbol, 0)
                if shares_owned < 100:
                    logger.info(
                        "Insufficient shares for covered call",
                        symbol=symbol,
                        shares_owned=shares_owned,
                        rule_id=rule.id,
                    )
                    continue

            # Fetch option chain
            raw_chain = await schwab_client.get_option_chain(
                symbol, min_dte=rule.min_dte, max_dte=rule.max_dte, contract_type=contract_type
            )
            iv_rank = iv_rank_tracker.get_iv_rank(symbol)
            candidates = parse_option_chain(raw_chain, iv_rank=iv_rank, contract_type=contract_type)

            # Resolve premium filter values based on mode
            min_premium_mode = getattr(rule, 'min_premium_mode', 'pct') or 'pct'
            min_premium_dollar_val = getattr(rule, 'min_premium_dollar', None)

            # New filter values
            strike_min = getattr(rule, 'strike_min', None)
            strike_max = getattr(rule, 'strike_max', None)
            max_premium_dollar_val = getattr(rule, 'max_premium_dollar', None)
            min_iv_pct = getattr(rule, 'min_iv_pct', None)
            max_iv_pct = getattr(rule, 'max_iv_pct', None)

            # Filter candidates
            passing = []
            for c in candidates:
                if not check_dte(c, rule.min_dte, rule.max_dte):
                    continue
                if strategy_type == "SELL_COVERED_CALL":
                    if not check_otm_call(c):
                        continue
                else:
                    if not check_otm_put(c):
                        continue
                # Strike range filter
                if strike_min is not None and c.strike < strike_min:
                    continue
                if strike_max is not None and c.strike > strike_max:
                    continue
                # Premium check — dollar mode bypasses pct check
                if min_premium_mode == 'dollar' and min_premium_dollar_val is not None:
                    if c.mid < min_premium_dollar_val:
                        continue
                    if max_premium_dollar_val is not None and c.mid > max_premium_dollar_val:
                        continue
                else:
                    if not check_premium_pct(c, rule.min_premium_pct, rule.max_premium_pct):
                        continue
                # Implied volatility % filter
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
                logger.info("No qualifying options found", symbol=symbol, rule_id=rule.id)
                continue

            # Select best candidate
            best = max(passing, key=lambda c: score_candidate(c, strategy_type))

            # Calculate position size
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
                    logger.info("Insufficient shares for covered call after sizing", symbol=symbol, shares_owned=shares_owned)
                    continue
            else:
                contracts = _calculate_contracts(best.strike, buying_power, rule, position_size_mode, position_size_contracts_val)
                if contracts < 1:
                    required = best.strike * 100
                    logger.info(
                        "Insufficient buying power for sell put",
                        symbol=symbol,
                        strike=best.strike,
                        required_per_contract=required,
                        available_buying_power=round(buying_power, 2),
                    )
                    continue

            results.append(TradeCandidate(rule=rule, candidate=best, contracts=contracts, symbol=symbol))
            open_count += 1

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
