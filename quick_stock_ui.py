"""First-tab automatic NSE stock research; one search, no buttons or uploads."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from market_universe import fallback_equities
from universe_ui import download_nse_equities
from quick_stock_core import stock_options, resolve_stock, analyze_stock_bars, IST


@st.cache_data(ttl=3600, show_spinner=False)
def catalog_for_search():
    """Official daily directory if accessible; clearly labeled fallback otherwise."""
    try:
        data = download_nse_equities()
        if len(data) < 100:
            raise ValueError("Incomplete official directory")
        return data, "NSE equity directory (cached; this is not a price feed)"
    except Exception:
        return fallback_equities(), "Partial built-in directory (NSE download unavailable)"


def render_auto_stock(tab, history):
    with tab:
        st.header("🔎 Auto Stock Assistant")
        st.write("**Simply select a company or type an NSE ticker.** Available research prices, technical evidence, an example paper plan and risks are calculated automatically.")
        st.caption("Default ₹50,000 paper capital · 1% risk · 25% maximum cash allocation · no broker connection or orders")
        catalog, catalog_label = catalog_for_search()
        options = stock_options(catalog)
        st.caption(f"Search source: {catalog_label} · {len(options):,} available symbols.")
        selection = st.selectbox(
            "Search NSE company name or ticker",
            options,
            index=None,
            placeholder="Type RELIANCE, TCS, Infosys, HDFCBANK…",
            accept_new_options=True,
            key="auto_stock_select",
            help="Choose a suggested company or enter its exact NSE ticker and press Enter.",
        )
        if not selection:
            st.info("Start typing in the box above. Once selected, the report appears automatically — no Analyze button.")
            return
        try:
            ticker, display, verified = resolve_stock(selection, options)
        except ValueError as exc:
            st.warning(str(exc))
            return
        if not verified:
            st.warning("The ticker is not verified in this directory. Confirm its NSE listing before interpreting provider results.")

        with st.expander("Optional: change the paper-trading budget", expanded=False):
            c1, c2, c3 = st.columns(3)
            capital = c1.number_input("Paper capital (₹)", min_value=1000.0,
                                      max_value=100000000.0, value=50000.0,
                                      step=1000.0, key="auto_stock_capital")
            risk = c2.number_input("Risk per idea (%)", min_value=0.1,
                                   max_value=5.0, value=1.0, step=0.1,
                                   key="auto_stock_risk")
            allocation = c3.number_input("Maximum one-stock allocation (%)",
                                         min_value=1.0, max_value=100.0,
                                         value=25.0, step=1.0,
                                         key="auto_stock_allocation")

        st.caption("This assistant requests actual research history even if another tab is in synthetic-demo mode. It does not use a licensed real-time feed.")
        try:
            with st.spinner("Getting historical prices and preparing an automatic research plan…"):
                bars, origin = history(ticker, "1d", "2y", False)
                report = analyze_stock_bars(
                    bars, capital=capital, risk_percent=risk,
                    allocation_percent=allocation,
                )
        except (ValueError, KeyError, TypeError, ZeroDivisionError, OverflowError) as exc:
            st.error("Market research cannot be completed right now — the price provider is unavailable or its data is incomplete.")
            st.caption(str(exc)[:240])
            st.info("No fake quote has been substituted. Try later or use Full-Market Scanner with real historical NSE CSV/ZIP files.")
            return

        snap, plan, budget = report["snapshot"], report["plan"], report["budget"]
        last = report["asof"].tz_convert(IST).strftime("%d %b %Y · %I:%M %p IST")
        st.subheader(display)
        st.caption(f"Historical source: {origin} · Latest daily bar: {last} · {snap['bars']} valid bars")
        if report["age_days"] > 7:
            st.error("Data is over seven days old. These levels are historical examples, not current trade references.")
        else:
            st.warning("Research-only daily closing prices; not a verified live quote. Delays, illiquidity and overnight gaps remain possible.")
        a, b, c, d = st.columns(4)
        a.metric("Historical last close", f"₹{snap['price']:,.2f}")
        b.metric("RSI (14)", f"{snap['rsi14']:.1f}")
        c.metric("20-session average", f"₹{snap['sma20']:,.2f}")
        d.metric("ATR (14)", f"₹{snap['atr14']:,.2f}")

        st.markdown("### Your automatic research result")
        st.info("**" + report["status"] + "** · " + snap["bias"])
        with st.expander("Explain the favorable factors and risks", expanded=True):
            st.markdown("**Favorable historical observations**")
            for reason in report["reasons"]:
                st.write("• " + reason)
            if not report["reasons"]:
                st.write("• No strong favorable indicator condition identified.")
            st.markdown("**Reasons to be cautious**")
            for reason in report["risks"]:
                st.write("• " + reason)
            st.write("• News events, liquidity, gaps, corporate actions, taxes and trading fees may alter outcomes.")

        st.markdown("### Example cash-share paper plan")
        x, y, z = st.columns(3)
        x.metric("Reference entry (last close)", f"₹{plan['entry']:,.2f}")
        y.metric("Illustrative stop (1.5×ATR)", f"₹{plan['stop']:,.2f}")
        z.metric("Illustrative target (2R)", f"₹{plan['target']:,.2f}")
        q1, q2, q3 = st.columns(3)
        q1.metric("Whole paper shares", str(budget["shares"]))
        q2.metric("Planned cash allocation", f"₹{budget['investment']:,.0f}")
        q3.metric("Planned loss incl. assumed slippage", f"₹{budget['planned_loss']:,.0f}")
        st.caption(
            f"Risk cap ₹{budget['risk_budget']:,.0f} · Hypothetical reward after assumed slippage ₹{budget['estimated_reward']:,.0f}. "
            "Includes illustrative 0.1% slippage each way, excludes other charges. Gaps can exceed planned loss."
        )
        if report["status"] != "CONDITIONAL WATCH — not a buy signal":
            st.warning("WAIT / NO TRADE for this evidence set. The numerical levels are research references, not an instruction to enter.")

        st.markdown("### Historical price and trend")
        chart = report["frame"].set_index("time").copy()
        chart["SMA20"] = chart["close"].rolling(20).mean()
        chart["SMA50"] = chart["close"].rolling(50).mean()
        st.line_chart(chart[["close", "SMA20", "SMA50"]].tail(180), height=300)

        with st.expander("Historical simulation (2,000 modeled paths; not a forecast)"):
            m = report["model"]
            s1, s2, s3 = st.columns(3)
            s1.metric("Target-first paths", f"{m['p_target_first']*100:.1f}%")
            s2.metric("Stop-first paths", f"{m['p_stop_first']*100:.1f}%")
            s3.metric("Neither reached", f"{m['p_neither']*100:.1f}%")
            st.caption("Historical daily-close resampling across 10 sessions, not calibrated future probabilities; not a live-market simulator.")

        st.link_button(
            "Verify NSE company announcements",
            "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
        )
        export = pd.DataFrame([{
            "Stock": ticker, "Source": origin, "Last historical bar IST": last,
            "Historical close": snap["price"], "Status": report["status"],
            "RSI14": round(snap["rsi14"], 2),
            "SMA20": round(snap["sma20"], 2),
            "ATR14": round(snap["atr14"], 2),
            "Illustrative entry": round(plan["entry"], 2),
            "Illustrative stop": round(plan["stop"], 2),
            "Illustrative target": round(plan["target"], 2),
            "Paper quantity": budget["shares"],
            "Planned loss": round(budget["planned_loss"], 2),
        }])
        st.download_button(
            "Export research summary (CSV)", export.to_csv(index=False),
            "auto_stock_research.csv", "text/csv", key="auto_stock_export",
        )
