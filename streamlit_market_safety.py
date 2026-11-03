"""Fail-closed Streamlit public-price protection for the legacy research prototype.

This module deliberately imports no Streamlit, pandas or external data provider
until the safe view is actually rendered. Default behavior requires no secrets.
It must not be treated as a market-data licence or SEBI legal approval.
"""
from __future__ import annotations

import os
import random
from datetime import date, timedelta


def streamlit_price_data_enabled() -> bool:
    """Two *server-only* opt-ins required; empty/unset flags always block."""
    return (
        os.environ.get("IML_STREAMLIT_PUBLIC_PRICE_ENABLED", "").strip().lower() == "true"
        and os.environ.get("IML_STREAMLIT_DATA_RIGHTS_APPROVED", "").strip().lower() == "true"
    )


def synthetic_demo_rows(count: int = 100, seed: int = 2121) -> list[dict]:
    """Artificial, reproducible series; no market symbols, providers or tickers."""
    if not isinstance(count, int) or not 2 <= count <= 260:
        raise ValueError("Synthetic example requires 2 to 260 observations")
    rng = random.Random(seed)
    # Date labels are illustrative and deliberately not tied to exchange sessions.
    day = date(2025, 1, 1)
    level = 100.0
    rows = []
    for index in range(count):
        level = max(20.0, level * (1 + rng.uniform(-0.018, 0.018)))
        rows.append({"Example step": (day + timedelta(days=index)).isoformat(),
                     "Synthetic index": round(level, 2)})
    return rows


def virtual_risk_budget(capital: float, risk_pct: float,
                        allocation_pct: float = 25.0) -> dict:
    """Only user-entered numbers; neither a quote nor a trading instruction."""
    if not (1000 <= capital <= 50_000_000 and 0.1 <= risk_pct <= 5
            and 1 <= allocation_pct <= 100):
        raise ValueError("Invalid virtual risk inputs")
    return {
        "virtual_capital": capital,
        "risk_percent": risk_pct,
        "virtual_risk_amount": round(capital * risk_pct / 100, 2),
        "allocation_cap": round(capital * allocation_pct / 100, 2),
    }


def render_safety_mode() -> None:
    """Synchronous stand-alone page. Never calls Yahoo, NSE or stock helpers."""
    import pandas as pd
    import streamlit as st

    st.title("Indian Market Lab")
    st.caption("Educational research sandbox · Market Data Safety Mode")
    st.error(
        "MARKET DATA SAFETY MODE — Public NSE stock-price data, named-stock "
        "trade plans, trading signals and historical scenarios are paused "
        "while data rights and regulatory requirements are reviewed."
    )
    st.info(
        "This independent Streamlit prototype now operates as a **synthetic "
        "learning sandbox**. Any chart on this page uses deliberately "
        "fabricated values, not actual market quotes. No orders, payments, "
        "brokers, portfolios or user registrations are connected."
    )

    overview, demo, budget, resources = st.tabs([
        "Safety status", "Synthetic learning example",
        "Virtual risk budget", "Resources"
    ])
    with overview:
        st.subheader("What is available")
        st.markdown(
            "- A clearly labeled fictional price-pattern example\n"
            "- User-controlled arithmetic for hypothetical risk budgeting\n"
            "- Independent regulatory and learning links\n\n"
            "**Temporarily unavailable:** Yahoo/NSE market quotes, "
            "real-company stock analysis, target/stop suggestions, "
            "market simulation from actual prices and the original "
            "Auto Stock Assistant."
        )
        st.caption("No actual exchange prices are collected or served by this page.")

    with demo:
        st.subheader("Synthetic index — fictional teaching example")
        st.warning(
            "SYNTHETIC DATA ONLY. The numbers below are randomly generated "
            "for education. They do not describe any NSE security or market."
        )
        count = st.slider("Example observations", 20, 200, 80, 20)
        frame = pd.DataFrame(synthetic_demo_rows(count)).set_index("Example step")
        st.line_chart(frame, height=330)
        st.caption(
            "Repeatable artificial sequence with zero market-price provider calls."
        )

    with budget:
        st.subheader("Paper-only risk arithmetic")
        st.caption(
            "This calculator uses only the values you enter. It does not "
            "select a security, share quantity, entry, stop, target, or trade."
        )
        a, b, c = st.columns(3)
        capital = a.number_input(
            "Hypothetical capital (₹)", min_value=1000.0,
            max_value=50_000_000.0, value=50_000.0, step=1000.0
        )
        risk = b.number_input(
            "Hypothetical risk (%)", min_value=0.1,
            max_value=5.0, value=1.0, step=0.1
        )
        allocation = c.number_input(
            "Maximum example allocation (%)", min_value=1.0,
            max_value=100.0, value=25.0, step=1.0
        )
        result = virtual_risk_budget(capital, risk, allocation)
        x, y = st.columns(2)
        x.metric("Virtual risk amount", f"₹{result['virtual_risk_amount']:,.2f}")
        y.metric("Illustrative allocation ceiling", f"₹{result['allocation_cap']:,.2f}")
        st.caption(
            "These are budget percentages, not executable orders or guaranteed "
            "maximum losses. Market losses may exceed any hypothetical budget."
        )

    with resources:
        st.markdown(
            "For the actively maintained, safety-restricted research website:\n\n"
            "https://indian-market-lab-fullstack.onrender.com\n\n"
            "Official references:\n\n"
            "- [SEBI](https://www.sebi.gov.in/)\n"
            "- [NSE data policy](https://www.nseindia.com/static/market-data/nse-data-policy)\n"
            "- [Terms of Use](https://indian-market-lab-fullstack.onrender.com/terms)\n"
            "- [Privacy Notice](https://indian-market-lab-fullstack.onrender.com/privacy)"
        )
    st.caption(
        "Indian Market Lab · Educational sandbox only · No real money or "
        "market data · Contact: rohanchhaya108@gmail.com"
    )
