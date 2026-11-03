"""Public scanner fail-closed policy and fictional-only demonstration.

Actual uploaded price files may have third-party data rights attached.
A named-security ranking can also raise investment research questions.
The public demonstration deliberately uses ONLY deterministic fake candles.
"""
from __future__ import annotations

import os
import random

import pandas as pd

from full_market_scanner import scan_market


SCANNER_PAUSED_NOTICE = (
    "Public uploads of actual stock-price files are temporarily unavailable "
    "while data-display rights and stock-specific research requirements are "
    "reviewed. The fictional scanner demo and user-entered risk tools remain "
    "available. No real orders or real quotes are provided."
)


def public_scanner_upload_enabled() -> bool:
    """Both server-only approvals are required; neither is a licence."""
    return (
        os.environ.get("IML_PUBLIC_SCANNER_UPLOAD_ENABLED", "").strip().lower() == "true"
        and os.environ.get("IML_SCANNER_COMPLIANCE_APPROVED", "").strip().lower() == "true"
    )


def public_scanner_status() -> dict:
    enabled = public_scanner_upload_enabled()
    return {
        "public_upload_enabled": enabled,
        "synthetic_demo_available": True,
        "no_orders": True,
        "note": ("Uploaded-file scanning requires proof of data rights and regulatory review."
                 if enabled else SCANNER_PAUSED_NOTICE),
    }


def synthetic_scanner_demonstration() -> dict:
    """Exercise real indicator engine using invented, NOT exchange, price bars.

    Do not return entry/stop/target/quantity fields, which are irrelevant to
    public educational demonstration and confusing next to real securities.
    """
    rng = random.Random(21219)
    dates = pd.bdate_range(end=pd.Timestamp.now().normalize(), periods=85)
    rows = []
    for symbol, start, trend in (("DEMOA", 100.0, 0.003), ("DEMOB", 120.0, -0.001)):
        price = start
        for day in dates:
            old = price
            price = max(5, old * (1 + trend + rng.uniform(-0.012, 0.012)))
            rows.append({
                "date": day,
                "symbol": symbol, "open": old,
                "high": max(old, price) * 1.005,
                "low": min(old, price) * 0.995,
                "close": price, "volume": rng.randrange(120_000, 160_000),
            })
    fictitious = pd.DataFrame(rows)
    ranked, summary = scan_market(
        fictitious, universe=None, capital=50_000,
        risk_pct=1, allocation_pct=25, min_turnover=0
    )
    items = []
    for _, x in ranked.iterrows():
        items.append({
            "Fictional series": str(x["Symbol"]),
            "Observations": int(x["Bars"]),
            "Example score /100": int(x["Score /100"]),
            "SMA20 (demo units)": float(x["SMA20 ₹"]),
            "SMA50 (demo units)": float(x["SMA50 ₹"]),
            "RSI14 (demo)": float(x["RSI14"]),
            "20-step change %": float(x["20d return %"]),
        })
    return {
        "synthetic": True,
        "source": "Deterministic, invented example data — not exchange prices",
        "no_trade_levels": True,
        "no_orders": True,
        "observations": len(fictitious),
        "fictional_series_count": len(items),
        "items": items,
        "note": ("All demonstration prices are fabricated; real NSE symbols, "
                 "quotes, recommendations, entry levels and paper quantities "
                 "are NOT included."),
    }
