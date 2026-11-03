"""Market Data Safety Mode contract tests; never contact real price providers."""
import pytest
from fastapi.testclient import TestClient

from fullstack.backend import main, terminal_engine as te
from fullstack.backend.market_data_safety import (
    public_market_data_enabled, public_market_data_safety_mode,
)

client = TestClient(main.app)


def close_market_data(monkeypatch):
    monkeypatch.delenv("IML_PUBLIC_PRICE_DATA_ENABLED", raising=False)
    monkeypatch.delenv("IML_MARKET_DATA_LICENSE_APPROVED", raising=False)


@pytest.mark.parametrize("enabled,licensed,expected", [
    (None, None, False),
    ("true", None, False),
    (None, "true", False),
    ("false", "true", False),
    ("true", "false", False),
    ("true", "true", True),
])
def test_double_operator_approval_required(monkeypatch, enabled, licensed, expected):
    for key, value in (
        ("IML_PUBLIC_PRICE_DATA_ENABLED", enabled),
        ("IML_MARKET_DATA_LICENSE_APPROVED", licensed),
    ):
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    assert public_market_data_enabled() is expected
    assert public_market_data_safety_mode() is (not expected)
    status = client.get("/api/market-data/status")
    assert status.status_code == 200
    assert status.json()["public_price_data_available"] is expected
    assert status.json()["market_data_safety_mode"] is (not expected)
    assert status.json()["real_orders"] is False


@pytest.mark.parametrize("route", [
    "/api/stock/RELIANCE/analysis",
    "/api/stock/RELIANCE/history?period=6mo",
    "/api/terminal/RELIANCE?interval=1d&lookback=6mo",
    "/api/terminal/TCS?interval=1m&lookback=1d",
])
def test_public_price_endpoints_blocked_before_provider_or_cache(monkeypatch, route):
    close_market_data(monkeypatch)
    monkeypatch.setattr(main, "yahoo_history",
                        lambda *args, **kw: (_ for _ in ()).throw(AssertionError("PROVIDER MUST NOT BE CALLED")))
    monkeypatch.setattr(main, "terminal_report",
                        lambda *args, **kw: (_ for _ in ()).throw(AssertionError("TERMINAL MUST NOT BE CALLED")))
    resp = client.get(route)
    assert resp.status_code == 503
    assert "market-data rights" in resp.json()["detail"]
    assert resp.headers.get("cache-control") == "no-store"


def test_helpers_refuse_market_data_even_if_invoked_directly(monkeypatch):
    close_market_data(monkeypatch)
    monkeypatch.setattr(main, "urlopen", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("network access")))
    monkeypatch.setattr(te, "urlopen", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("network access")))
    with pytest.raises(ValueError, match="disabled"):
        main.yahoo_history("RELIANCE", "1y")
    with pytest.raises(ValueError, match="disabled"):
        te.fetch_candles("RELIANCE", "1d", "6mo")


def test_non_price_tools_stay_available_and_symbol_directory_is_offline(monkeypatch):
    close_market_data(monkeypatch)
    monkeypatch.setattr(main, "urlopen", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("directory network access")))
    directory, origin = main.symbol_directory()
    assert len(directory) > 0
    assert "offline" in origin.lower()
    assert client.get("/api/universe?q=RELIANCE").status_code == 200
    assert client.get("/api/terminal/universe?q=TCS").status_code == 200
    assert client.get("/api/indices").status_code == 200
    assert client.post("/api/risk/plan",
                       json={"entry": 1000, "stop": 950, "target": 1100}).status_code == 200
    derivative = client.post("/api/derivatives/plan", json={"kind": "Call (CE)", "premium": 20, "lot_size": 75})
    assert derivative.status_code == 200
    assert derivative.json()["no_order_execution"] is True
    assert client.get("/api/health").json()["real_orders"] is False


def close_scanner_uploads(monkeypatch):
    monkeypatch.delenv("IML_PUBLIC_SCANNER_UPLOAD_ENABLED", raising=False)
    monkeypatch.delenv("IML_SCANNER_COMPLIANCE_APPROVED", raising=False)


@pytest.mark.parametrize("enabled,approved,expected", [
    (None, None, False),
    ("true", None, False),
    (None, "true", False),
    ("false", "true", False),
    ("true", "false", False),
    ("true", "true", True),
])
def test_scanner_requires_both_operator_approvals(monkeypatch, enabled, approved, expected):
    from fullstack.backend.scanner_safety import public_scanner_upload_enabled
    for key, value in (
        ("IML_PUBLIC_SCANNER_UPLOAD_ENABLED", enabled),
        ("IML_SCANNER_COMPLIANCE_APPROVED", approved),
    ):
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    assert public_scanner_upload_enabled() is expected
    s = client.get("/api/scanner/status")
    assert s.status_code == 200
    assert s.json()["public_upload_enabled"] is expected
    assert s.json()["synthetic_demo_available"] is True
    assert s.headers["cache-control"] == "no-store"


def test_public_scanner_upload_fails_before_parsing(monkeypatch):
    close_scanner_uploads(monkeypatch)
    close_market_data(monkeypatch)
    monkeypatch.setattr(main, "parse_price_uploads",
                        lambda *_: (_ for _ in ()).throw(AssertionError("PARSER MUST NOT BE CALLED")))
    response = client.post("/api/scanner/import", files=[
        ("files", ("history.csv", b"date,symbol,close\n2026-10-30,RELIANCE,100", "text/csv"))
    ])
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]
    assert response.headers.get("cache-control") == "no-store"
    assert response.headers.get("x-frame-options") == "DENY"


def test_synthetic_demo_preserves_descriptive_indicators_without_trade_levels(monkeypatch):
    close_scanner_uploads(monkeypatch)
    close_market_data(monkeypatch)
    monkeypatch.setattr(main, "urlopen",
                        lambda *_a, **_kw: (_ for _ in ()).throw(AssertionError("PROVIDER CALLED")))
    r = client.get("/api/scanner/demo")
    assert r.status_code == 200, r.text
    assert r.headers["cache-control"] == "no-store"
    data = r.json()
    assert data["synthetic"] is True
    assert data["no_trade_levels"] is True
    assert data["no_orders"] is True
    assert data["observations"] == 170
    assert data["fictional_series_count"] == 2
    assert set(row["Fictional series"] for row in data["items"]) == {"DEMOA", "DEMOB"}
    forbidden = {"Symbol", "Company", "Status", "Paper entry ref ₹",
                 "Paper stop ref ₹", "Paper 2R target ₹", "Paper shares",
                 "Paper allocated ₹", "Max planned loss ₹"}
    assert all(not forbidden.intersection(row) for row in data["items"])
    assert client.get("/api/beta/status").json()["waitlist_open"] is False


def test_public_interface_has_explicit_safe_mode_notice(monkeypatch):
    close_market_data(monkeypatch)
    assert "market-data-banner" in client.get("/app.js").text
    assert "market-data-safety-banner" in client.get("/terminal").text
    assert "showMarketDataSafety" in client.get("/terminal.js").text
    assert "/api/market-data/status" in client.get("/terminal.js").text
    assert "Market Data Safety Mode" in client.get("/pages/stocks.js").text
    assert "market_data_safety_mode" in client.get("/api/terminal/config").json()
    beta = client.get("/api/beta/status").json()
    assert beta["waitlist_open"] is False
    assert beta["feedback_open"] is False
