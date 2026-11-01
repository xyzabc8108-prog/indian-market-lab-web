"""Pure stock search and risk calculations for the no-click stock assistant.

No fabricated market quotes, broker access, or promised trade outcomes.
"""
from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

from research_engine import (
    validate_ohlcv, technical_snapshot, planning_levels,
    position_budget, scenario_simulation,
)

IST = ZoneInfo("Asia/Kolkata")
SYMBOL = re.compile(r"^[A-Z0-9][A-Z0-9&-]{0,19}$")


def stock_options(catalog: pd.DataFrame) -> list[str]:
    if not {"Symbol", "Company"}.issubset(catalog.columns):
        raise ValueError("Catalog needs Symbol and Company columns")
    entries, seen = [], set()
    for symbol, company in catalog[["Symbol", "Company"]].itertuples(index=False, name=None):
        symbol, company = str(symbol).strip().upper(), str(company).strip()
        if SYMBOL.fullmatch(symbol) and symbol not in seen:
            seen.add(symbol)
            entries.append(f"{symbol} — {company[:90]}" if company else symbol)
    return sorted(entries, key=lambda option: option.split(" — ", 1)[0])


def resolve_stock(value: str, options: list[str]) -> tuple[str, str, bool]:
    """Return (provider ticker, display label, verified in loaded directory)."""
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("Choose a stock or enter its NSE ticker.")
    exact = next((o for o in options if o.casefold() == raw.casefold()), None)
    if exact:
        symbol = exact.split(" — ", 1)[0].upper()
        return symbol + ".NS", exact, True
    code = raw.upper().removeprefix("NSE:").removesuffix(".NS").strip()
    mapping = [(o.split(" — ", 1)[0], o.split(" — ", 1)[-1]) for o in options]
    symbols = dict(mapping)
    if code in symbols:
        return code + ".NS", f"{code} — {symbols[code]}", True
    same_name = [(sym, company) for sym, company in mapping if company.casefold() == raw.casefold()]
    if len(same_name) == 1:
        sym, company = same_name[0]
        return sym + ".NS", f"{sym} — {company}", True
    if len(same_name) > 1:
        raise ValueError("Ambiguous company name; select its exact NSE symbol.")
    if SYMBOL.fullmatch(code):
        return code + ".NS", code + " — unverified ticker", False
    raise ValueError("Choose a listed stock or enter a valid NSE ticker such as INFY.")


def analyze_stock_bars(
    bars: pd.DataFrame,
    capital: float = 50000.0,
    risk_percent: float = 1.0,
    allocation_percent: float = 25.0,
    as_of: datetime | None = None,
    simulation_paths: int = 2000,
) -> dict:
    frame = validate_ohlcv(bars)
    snap = technical_snapshot(frame)
    plan = planning_levels(snap, direction="Long", atr_multiple=1.5, target_multiple=2)
    budget = position_budget(
        capital, risk_percent, allocation_percent,
        plan["entry"], plan["stop"], plan["target"], slippage_pct_per_side=0.10
    )
    now = pd.Timestamp(as_of if as_of is not None else datetime.now(IST))
    if now.tzinfo is None:
        raise ValueError("Analysis timestamp must include a timezone")
    last = pd.Timestamp(snap["asof"])
    if last.tzinfo is None:
        raise ValueError("Market bar missing timezone")
    age_days = max(0.0, (now - last).total_seconds() / 86400)
    favorable, risks = [], []
    if snap["price"] > snap["sma20"]:
        favorable.append("Closing price is above the 20-session average.")
    else:
        risks.append("Closing price is below the 20-session average.")
    if snap["sma50"] is not None:
        if snap["sma20"] > snap["sma50"]:
            favorable.append("20-session average is above the 50-session average.")
        else:
            risks.append("20-session average is below the 50-session average.")
    if snap["price"] > snap["resistance20"]:
        favorable.append("Close is above the previous 20-session high.")
    else:
        risks.append("No confirmed close above the previous 20-session high.")
    if snap["rsi14"] > 75:
        risks.append("Elevated RSI; a pullback remains possible.")
    elif snap["rsi14"] < 30:
        risks.append("Very weak RSI; downside momentum may persist.")
    if age_days > 7:
        risks.insert(0, "Latest bar is over seven calendar days old.")
    if len(frame) < 60:
        risks.append("Fewer than 60 historical sessions.")
    if budget["no_trade"]:
        risks.append("No whole-share position fits the allocation and risk limits.")
    if age_days > 7:
        status = "STALE DATA — no current trade plan"
    elif len(frame) < 60:
        status = "INSUFFICIENT HISTORY — wait"
    elif budget["no_trade"]:
        status = "NO POSITION WITHIN BUDGET"
    elif snap["bias"] != "Upward evidence" or snap["rsi14"] > 75:
        status = "WAIT / NO-TRADE — limited bullish confirmation"
    else:
        status = "CONDITIONAL WATCH — not a buy signal"
    model = scenario_simulation(
        frame, plan["entry"], plan["stop"], plan["target"],
        paths=simulation_paths, horizon=10, seed=2026,
    )
    return {
        "frame": frame, "snapshot": snap, "plan": plan, "budget": budget,
        "age_days": age_days, "reasons": favorable, "risks": risks,
        "status": status, "model": model, "asof": last,
    }
