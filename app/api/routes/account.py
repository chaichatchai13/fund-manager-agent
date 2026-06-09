from datetime import date
from fastapi import APIRouter

router = APIRouter(prefix="/api/account", tags=["account"])


def _parse_holdings(positions: list) -> list:
    """Parse Schwab account positions into a flat holdings list."""
    holdings = []
    today = date.today()
    for pos in positions:
        instrument = pos.get("instrument", {})
        asset_type = instrument.get("assetType", "EQUITY")
        symbol = instrument.get("symbol", "")
        description = instrument.get("description", symbol)

        if asset_type == "EQUITY":
            holdings.append({
                "symbol": symbol,
                "description": description,
                "asset_type": "EQUITY",
                "quantity": pos.get("longQuantity", 0) - pos.get("shortQuantity", 0),
                "market_value": pos.get("marketValue"),
                "day_change_pct": pos.get("currentDayProfitLossPercentage"),
                "average_price": pos.get("averagePrice"),
            })
        elif asset_type == "OPTION":
            exp_str = instrument.get("expirationDate", "")
            dte = None
            if exp_str:
                try:
                    exp_date = date.fromisoformat(exp_str[:10])
                    dte = (exp_date - today).days
                except ValueError:
                    pass

            # Schwab may return putCall as "PUT"/"CALL" on the instrument
            # or it can be inferred from the option symbol (e.g. ...C00048000 = CALL)
            put_call = instrument.get("putCall") or instrument.get("put_call")
            if not put_call:
                # Fallback: infer from symbol — look for 'C' or 'P' before the strike digits
                import re
                m = re.search(r'[CP]\d{8}', symbol)
                if m:
                    put_call = "CALL" if m.group(0).startswith("C") else "PUT"

            holdings.append({
                "symbol": symbol,
                "description": description,
                "asset_type": "OPTION",
                "quantity": pos.get("longQuantity", 0) - pos.get("shortQuantity", 0),
                "market_value": pos.get("marketValue"),
                "day_change_pct": pos.get("currentDayProfitLossPercentage"),
                "average_price": pos.get("averagePrice"),
                "strike": instrument.get("strikePrice"),
                "expiration_date": exp_str[:10] if exp_str else None,
                "put_call": put_call,
                "dte": dte,
            })
    return holdings


@router.get("")
async def get_account():
    from app.schwab.client import schwab_client
    if not schwab_client.is_connected:
        return {
            "portfolio_value": None,
            "buying_power": None,
            "cash_balance": None,
            "holdings": [],
            "schwab_connected": False,
        }
    account = await schwab_client.get_account()
    securities = account.get("securitiesAccount", {})
    balances = securities.get("currentBalances", {})
    positions = securities.get("positions", [])

    # "buyingPower" in Schwab = margin buying power (may be 2× equity for margin accounts)
    # "cashBalance" or "availableFunds" reflects actual cash available for cash-secured trades
    raw_buying_power = balances.get("buyingPower")
    available_funds = balances.get("availableFunds") or balances.get("availableFundsNonMarginableTrade")
    cash_balance = balances.get("cashBalance")

    # Use the most conservative non-zero value as "available for sell puts"
    # (avoids margin inflation for cash-secured strategies)
    _candidates = [v for v in [available_funds, cash_balance] if v is not None and v > 0]
    sell_put_buying_power = min(_candidates) if _candidates else raw_buying_power

    return {
        "portfolio_value": balances.get("liquidationValue"),
        "buying_power": raw_buying_power,           # raw Schwab value (may be margin 2×)
        "cash_balance": cash_balance,
        "available_funds": available_funds,
        "sell_put_buying_power": sell_put_buying_power,  # used by rule engine for sizing
        "holdings": _parse_holdings(positions),
        "schwab_connected": True,
    }


@router.post("/scan")
async def trigger_scan(rule_id: str | None = None):
    from app.services.scan_service import scan_service
    position_ids = await scan_service.run_scan(rule_id=rule_id)
    return {"positions_created": len(position_ids), "position_ids": position_ids}
