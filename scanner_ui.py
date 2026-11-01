"""Phase 1: validated full-market NSE cash-equity Streamlit scanner."""
import pandas as pd
import streamlit as st
from full_market_scanner import parse_price_uploads,scan_market,MIN_SESSIONS
from nse_bundle import load_nse_bundle
from market_universe import load_equity_csv

def render_full_market_scanner(tab):
    with tab:
        st.subheader("Full-Market Scanner · NSE equity")
        st.caption("Real uploaded EOD prices only • INR • paper cash positions • no orders")
        st.info("This scans ALL NSE equity symbols covered by your uploaded price history. A securities-directory ZIP is not a price history. Uncovered symbols cannot be ranked.")
        with st.expander("1 · Upload NSE equity securities directory",expanded=True):
            catalog_file=st.file_uploader("Upload NSE.zip (recommended) or EQUITY_L.csv",type=["zip","csv"],key="phase1_catalog")
            universe=None
            if catalog_file is not None:
                try:
                    body=catalog_file.getvalue()
                    universe=(load_nse_bundle(body) if catalog_file.name.lower().endswith(".zip") else load_equity_csv(body))
                    if "Asset type" in universe:
                        universe=universe[universe["Asset type"].isin(["Mainboard equity","SME equity"])]
                    if "Series" in universe:
                        universe=universe[universe["Series"].astype(str).str.upper().eq("EQ")]
                    universe=universe.drop_duplicates("Symbol")
                    st.success(f"{len(universe):,} eligible equity symbols loaded — directory only.")
                except (ValueError,TypeError) as exc:
                    st.error("Invalid symbol directory: "+str(exc));st.stop()
            else:
                st.warning("No universe uploaded: only EQ symbols in your uploaded price history can be scanned. This is NOT verified full-market coverage.")
        with st.expander("2 · Upload daily OHLCV history",expanded=True):
            st.write("Download CM-UDiFF Common Bhavcopy Final (ZIP) for many trade dates from the official NSE daily reports. Alternatively upload a historical CSV with date,symbol,open,high,low,close,volume.")
            st.link_button("NSE official daily reports","https://www.nseindia.com/all-reports")
            files=st.file_uploader("Upload price ZIP/CSV files across multiple sessions",
                                   type=["zip","csv"],accept_multiple_files=True,key="phase1_prices")
            st.caption(f"At least {MIN_SESSIONS} distinct daily sessions PER stock are mandatory. A one-day file supports no multi-day technical ranking.")
        st.divider()
        st.markdown("#### 3 · Fixed paper budget")
        a,b,c=st.columns(3)
        capital=a.number_input("Paper capital ₹",1000.,100_000_000.,50_000.,1000.,key="phase1_capital")
        risk_pct=b.number_input("Max planned risk per trade (%)",.1,5.,1.,.1,key="phase1_risk")
        cap_pct=c.number_input("Maximum allocation per stock (%)",1.,100.,25.,1.,key="phase1_alloc")
        turnover=st.number_input("Min 20-day average rupee turnover ₹",0.,1_000_000_000.,2_000_000.,500_000.,key="phase1_turnover")
        st.caption(f"At these settings: planned-risk cap ₹{capital*risk_pct/100:,.0f}; single-stock cash allocation cap ₹{capital*cap_pct/100:,.0f}. Real gaps may exceed the planned loss.")
        fingerprint=(tuple((f.name,f.size) for f in (files or [])),
                     catalog_file.name if catalog_file else None,capital,risk_pct,cap_pct,turnover)
        if st.button("Validate price files & scan the market",type="primary",disabled=not bool(files),key="phase1_go"):
            try:
                with st.spinner("Validating OHLCV and calculating historical signals…"):
                    bars,quality=parse_price_uploads([(f.name,f.getvalue()) for f in files])
                    ranked,summary=scan_market(bars,universe,capital,risk_pct,cap_pct,turnover)
                    st.session_state["phase1_result"]=(ranked,summary,quality,fingerprint)
            except (ValueError,MemoryError,OverflowError) as exc:
                st.session_state.pop("phase1_result",None)
                st.error("Cannot scan: "+str(exc))
        if "phase1_result" not in st.session_state:
            st.caption("No price scan has run. Upload 60+ dates for supported stocks, then click Scan.")
            return
        ranked,summary,quality,last_fingerprint=st.session_state.phase1_result
        if fingerprint!=last_fingerprint:
            st.warning("Your input files or budget settings changed. Click Scan again before relying on these results.")
            return
        st.markdown("#### Data-quality and coverage audit")
        a,b,c=st.columns(3)
        a.metric("Validated price rows",f"{quality['Price rows']:,}")
        b.metric("Price symbols",f"{quality['Symbols with some data']:,}")
        c.metric("Scannable after history checks",f"{len(ranked):,}")
        st.write(f"Snapshot session: {summary['Latest market date in upload']} · Under 60 bars: {summary['Insufficient history']:,} · Lacking recent bars: {summary['Missing recent bars']:,} · Conflicting duplicates rejected: {quality['Conflicting symbol-dates dropped']:,}")
        if summary["File age days"]>7:
            st.warning(f"Snapshot is {summary['File age days']} days old. These are historical scores, NOT today's opportunities.")
        if quality["Skipped details"]:
            with st.expander(f"Skipped files ({quality['Files skipped']})"):
                for issue in quality["Skipped details"]:st.write(issue)
        if ranked.empty:
            st.error("No instruments have 60 recent dated sessions within the supplied price snapshot. Import more days, verify EQ series and ensure universe symbols overlap.")
            return
        st.markdown("#### Ranked securities — explicit, non-predictive rules")
        status=st.multiselect("Status",["REVIEW CANDIDATE","WATCH / NO PAPER ENTRY"],
                             default=["REVIEW CANDIDATE","WATCH / NO PAPER ENTRY"],key="phase1_status")
        visible=ranked[ranked["Status"].isin(status)]
        columns=["Symbol","Company","Last date","Last close ₹","Score /100","20d return %",
                 "RSI14","Rel volume","Avg turnover ₹","Status","Paper shares",
                 "Paper stop ref ₹","Paper 2R target ₹","Max planned loss ₹"]
        st.dataframe(visible[columns],hide_index=True,use_container_width=True,height=420)
        st.download_button("Export full ranked CSV",ranked.to_csv(index=False),
                           "nse_full_market_rankings.csv","text/csv",key="phase1_download")
        st.caption("Heuristic score (NOT win probability): trend 25 + momentum 20 + liquidity 15 + RSI 10 + breakout 15 + relative volume 15 = 100.")
        st.markdown("#### Explain one stock")
        chosen=st.selectbox("Select symbol",ranked["Symbol"].tolist(),key="phase1_symbol")
        row=ranked[ranked["Symbol"]==chosen].iloc[0]
        a,b,c=st.columns(3)
        a.metric("Historical score",f"{int(row['Score /100'])}/100")
        b.metric("Risk-budgeted shares",int(row["Paper shares"]))
        c.metric("Ideal stop loss before fees",f"₹{row['Max planned loss ₹']:,.2f}")
        st.write("**Status:**",row["Status"])
        st.write("**Evidence:**",row["Reasons"] or "No positive evidence in this model.")
        st.write("**Risks:**",row["Risks"] or "No additional rule-based flags; uncertainty remains.")
        points=["Trend /25","Momentum /20","Liquidity /15","RSI /10","Breakout /15","Volume /15"]
        st.dataframe(pd.DataFrame({"Component":points,"Points":[row[x] for x in points]}),
                     hide_index=True,use_container_width=True)
        st.warning("Paper stop and 2R target are reference levels based on the last close and ATR14. Real fills may gap or slip; charges, corporate actions and execution constraints are excluded. No orders are placed.")
