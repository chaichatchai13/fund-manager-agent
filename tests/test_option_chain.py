"""Tests for option chain parsing."""
from app.schwab.client import _mock_option_chain
from app.schwab.option_chain import parse_option_chain


def test_parse_mock_chain_tsla():
    raw = _mock_option_chain("TSLA", min_dte=30, max_dte=45)
    candidates = parse_option_chain(raw, iv_rank=60.0)

    assert len(candidates) > 0
    for c in candidates:
        assert c.underlying == "TSLA"
        assert c.stock_price == 351.0
        assert c.strike < c.stock_price  # all OTM
        assert c.mid > 0
        assert c.dte == 35
        assert c.iv_rank == 60.0


def test_parse_mock_chain_iren():
    raw = _mock_option_chain("IREN", min_dte=30, max_dte=45)
    candidates = parse_option_chain(raw, iv_rank=45.0)
    assert all(c.stock_price == 8.50 for c in candidates)
