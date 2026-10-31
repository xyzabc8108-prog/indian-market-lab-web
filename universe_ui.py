"""Browser UI for full NSE symbol search + selected-instrument quote/replay.

Catalog lookup is not a live feed. Research quotes are potentially delayed.
"""
from __future__ import annotations
import math
import re
from datetime import datetime
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from market_universe import (
    EQUITY_URL, NSE_LIST_PAGE, NSE_INDICES_PAGE,
    load_equity_csv, fallback_equities, load_index_csv, indices_table,
    filter_catalog, quote_age_minutes, paper_replay,
)

IST=ZoneInfo('Asia/Kolkata')

@st.cache_data(ttl=86400,show_spinner=False)
def download_nse_equities() -> pd.DataFrame:
    """Daily-cached NSE public instrument directory, not NSE market prices."""
    req=Request(EQUITY_URL,headers={'User-Agent':'Mozilla/5.0','Accept':'text/csv,*/*'})
    with urlopen(req,timeout=12) as resp:
        if resp.status!=200:
            raise RuntimeError('NSE instrument server returned HTTP '+str(resp.status))
        raw=resp.read(8_000_001)
    return load_equity_csv(raw)


def parse_bhavcopy(raw:bytes) -> pd.DataFrame:
    """Optional user-supplied CSV of end-of-day data for broad market screening."""
    if not raw or len(raw)>6_000_000: raise ValueError('CSV must be under 6 MB.')
    try:df=pd.read_csv(__import__('io').BytesIO(raw),low_memory=False)
    except Exception as exc:raise ValueError('Could not read the EOD CSV') from exc
    df.columns=[str(c).strip().upper().replace(' ','_') for c in df.columns]
    sym=next((c for c in ('SYMBOL','TCKRSYMB','TICKER') if c in df),None)
    close=next((c for c in ('CLOSE_PRICE','CLOSE','CLS_PRICE','CLS_PRC','CLSPRIC') if c in df),None)
    if sym is None or close is None:
        raise ValueError('Needs a symbol column and close price column (e.g. SYMBOL and CLOSE_PRICE).')
    out=pd.DataFrame({'Symbol':df[sym].astype(str).str.strip(),
                      'Close ₹':pd.to_numeric(df[close],errors='coerce')})
    out=out.dropna(subset=['Close ₹'])
    out=out[out['Close ₹']>0]
    for label,candidates in [('Open ₹',('OPEN_PRICE','OPEN','OPN_PRICE','OPNPRIC')),
                              ('High ₹',('HIGH_PRICE','HIGH','HGH_PRICE','HGHPRIC')),
                              ('Low ₹',('LOW_PRICE','LOW','LW_PRICE','LWPRIC')),
                              ('Volume',('TTL_TRD_QNTY','TOTTRDQTY','TOTTRDQTY','VOLUME','TTLTRDQTY'))]:
        col=next((c for c in candidates if c in df),None)
        if col:
            out[label]=pd.to_numeric(df.loc[out.index,col],errors='coerce')
    return out.head(10000).reset_index(drop=True)


def render_universe(tab,history,mode):
    """Shows searchable reference universe, one-instrument quotes and paper replay."""
    with tab:
        st.subheader('NSE stock & index directory · quote replay')
        if not st.toggle('Load directory and market tools', value=False, key='universe_activate'):
            st.caption('Activate this page to load an official stock directory (or upload CSV) and analyze selected prices. This avoids slow exchange requests elsewhere in the app.')
            return
        st.info('Search the full official NSE equity list when available. This is a symbol DIRECTORY, not a real-time feed of every stock. Only your selected instrument fetches a research quote. Prices may be delayed or unavailable.')
        st.caption('No brokerage access, no orders, no authenticated exchange feed. All monetary values in INR; displayed bar times in IST.')
        with st.expander('Directory source / upload official NSE stock or index CSV',expanded=False):
            st.link_button('NSE securities list (official)',NSE_LIST_PAGE)
            st.link_button('NSE index list (official)',NSE_INDICES_PAGE)
            uploaded=st.file_uploader('Official NSE EQUITY_L.csv (optional if Cloud download is blocked)',type='csv',key='universe_equity_upload')
            index_uploaded=st.file_uploader('Optional index directory CSV (Index, Group, Yahoo Ticker)',type='csv',key='universe_index_upload')
            if st.button('Retry official equity download',key='nse_download_retry'): download_nse_equities.clear()
        try:
            if uploaded:
                universe=load_equity_csv(uploaded.getvalue());source='Uploaded NSE equity reference CSV (static)'
            else:
                universe=download_nse_equities();source='Official NSE equity reference CSV (daily cached)'
        except Exception as exc:
            universe=fallback_equities()
            source='Small built-in sample only — NOT the complete listed universe'
            st.warning('The official NSE CSV could not be fetched from this server: '+str(exc)[:200]+'. Download the CSV from NSE on your PC and upload it above to search all its listed symbols.')
        try:
            indices=load_index_csv(index_uploaded.getvalue()) if index_uploaded else indices_table()
            index_source='User-uploaded index directory' if index_uploaded else 'Built-in representative index directory (not exhaustive)'
        except ValueError as exc:
            st.warning('Index CSV error: '+str(exc));indices=indices_table();index_source='Built-in index directory'
        a,b=st.columns(2)
        a.metric('Equity entries loaded',f'{len(universe):,}')
        b.metric('Index names loaded',f'{len(indices):,}')
        st.caption('Equities: '+source+' · Indices: '+index_source)
        kind=st.radio('Explore',('NSE equities','Indices'),horizontal=True,key='market_kind')
        search=st.text_input('Search by name, symbol or index',placeholder='e.g. RELIANCE, SBI, NIFTY',key='universe_search')
        table=filter_catalog(universe if kind=='NSE equities' else indices,search,limit=150)
        st.dataframe(table,use_container_width=True,hide_index=True,height=285)
        st.caption('Showing up to 150 search results at once. Type to narrow; a complete downloaded directory can contain thousands of symbols.')
        if table.empty:
            st.info('No match in the loaded directory; try a different search or upload the official CSV.')
            return
        if kind=='NSE equities':
            symbols=table['Symbol'].astype(str).tolist()
            selected=st.selectbox('Choose a listed stock',symbols,key='universe_selected_stock')
            ticker=str(table.loc[table['Symbol']==selected,'Provider ticker'].iloc[0])
            caption='NSE equity: '+selected
        else:
            names=table['Index'].astype(str).tolist()
            selected=st.selectbox('Choose an index',names,key='universe_selected_index')
            ticker=str(table.loc[table['Index']==selected,'Yahoo ticker'].iloc[0] or '')
            caption='Index: '+selected
            if not ticker:st.warning('This index has no VERIFIED Yahoo ticker mapping. You can enter a provider ticker manually, but verify the symbol and returned instrument before relying on its data.')
            if not ticker:
                ticker=st.text_input('Optional Yahoo Finance index ticker (unverified, e.g. ^NSEI)',value='',key='universe_manual_ticker').strip().upper()
        if ticker and not re.fullmatch(r'[\^A-Z0-9&._-]{2,30}',ticker):
            st.error('Invalid provider ticker.');return
        st.divider()
        st.subheader('Selected-instrument price & auto-refresh')
        st.caption('The page can re-check one selected instrument every 5 minutes while your browser session is active. Refreshing the page does NOT make delayed upstream quotes real-time.')
        auto=st.toggle('Auto-refresh selected quote every 5 minutes',value=False,key='universe_autorefresh')
        @st.fragment(run_every='300s' if auto else None)
        def selected_quote():
            if not ticker:
                st.info('Enter a verified Yahoo index symbol to check prices.');return
            try:
                bars,source_name=history(ticker,'5m','5d',mode=='Synthetic demo')
                if bars.empty:raise ValueError('No bars returned')
                latest=bars.iloc[-1]
                age=quote_age_minutes(latest['time'])
                name=caption+' · '+ticker
                st.write('**'+name+'**')
                c1,c2,c3=st.columns(3)
                c1.metric('Latest supplied close/reference',f"₹{float(latest['close']):,.2f}")
                c2.metric('Age of latest bar',f'{age:,.0f} minutes')
                c3.metric('Bars loaded',f'{len(bars):,}')
                when=pd.Timestamp(latest['time']).strftime('%d %b %Y %I:%M %p IST')
                st.caption('Source: '+source_name+' · Last bar: '+when+' · Browser checked at '+datetime.now(IST).strftime('%I:%M:%S %p IST'))
                if mode=='Synthetic demo':
                    st.error('FABRICATED DATA — demonstration only. This is NOT the NSE price.')
                elif age>15:
                    st.warning('Stale bar (>15 minutes old). This can be normal outside market hours. Do not treat as an executable quote.')
                else:
                    st.info('Research data timestamp shown; exchange-verified real-time status and data-use permission are NOT established.')
                st.line_chart(bars.set_index('time')[['close']],height=260)
                with st.expander('Historical paper-trade replay (no order execution)',expanded=False):
                    if len(bars)<3:
                        st.warning('At least three bars are needed.')
                    else:
                        a,b=st.columns(2)
                        entry_bar=a.slider('Hypothetical entry at this already revealed bar close',0,len(bars)-2,max(0,len(bars)-30),key='universe_entry_bar')
                        end_bar=b.slider('Replay the price path only through this bar',entry_bar+1,len(bars)-1,len(bars)-1,key='universe_end_bar')
                        pc=float(bars.iloc[entry_bar]['close'])
                        x,y,z=st.columns(3)
                        cap=x.number_input('Paper capital ₹',min_value=1000.,value=50000.,step=1000.,key='universe_capital')
                        risk=y.number_input('Risk per idea %',min_value=.1,max_value=5.,value=1.,step=.1,key='universe_risk')
                        stop_dist=z.number_input('Stop distance %',min_value=.1,max_value=25.,value=2.,step=.5,key='universe_stop_pct')
                        stop=pc*(1-stop_dist/100)
                        target=pc+2*(pc-stop)
                        qty=int(min(math.floor(cap*risk/100/(pc-stop)), math.floor(cap/pc))) if stop>0 else 0
                        st.caption(f'Paper entry ₹{pc:.2f}, stop ₹{stop:.2f}, 2R target ₹{target:.2f}, whole shares {qty}. Before charges/slippage; stop execution may be worse.')
                        if qty==0:st.warning('Insufficient capital/risk budget. No hypothetical position.')
                        else:
                            try:
                                result=paper_replay(bars.reset_index(drop=True),entry_bar,end_bar,qty,stop,target)
                                c1,c2,c3=st.columns(3)
                                c1.metric('Replay status',result['status'])
                                c2.metric('P&L before costs',f"₹{result['pnl_before_costs']:+,.2f}")
                                c3.metric('Reference exit ₹',f"₹{result['exit_ref']:,.2f}")
                                st.line_chart(bars.iloc[:end_bar+1].set_index('time')[['close']],height=180)
                                if result['intrabar_ambiguous']:
                                    st.warning('Stop and target were both crossed within a single candle. Without tick order, the sequence cannot be known; a conservative stop-first assumption was used.')
                                if result['gap_assumption']:
                                    st.warning('A price gap crossed the stop/target at the next bar open; this is a simplified reference, not an executable fill.')
                                st.caption('Educational historical bar-by-bar replay only. The model never sees future bars beyond the replay cursor. Results exclude brokerage, taxes and transaction friction.')
                            except ValueError as exc:st.warning(str(exc))
                st.download_button('Download selected history CSV',bars.to_csv(index=False),file_name='selected_market_bars.csv',mime='text/csv',key='universe_history_dl')
            except (ValueError,KeyError,TypeError,IndexError) as exc:
                st.error('Selected symbol data unavailable: '+str(exc))
                st.info('You can still search the reference directory or upload EOD data. If Yahoo blocks the cloud host, a licensed feed is required for reliable public quotes.')
        selected_quote()
        st.divider()
        with st.expander('Analyze ALL stocks at once from an official end-of-day CSV (not live)',expanded=False):
            st.caption('Download NSE daily security report / bhavcopy and upload it. This screens a whole market snapshot in one operation; no thousands of individual quote calls.')
            report=st.file_uploader('Official NSE equity EOD report (CSV)',type=['csv'],key='universe_eod_upload')
            if report:
                try:
                    whole=parse_bhavcopy(report.getvalue())
                    st.metric('Rows in this EOD snapshot',f'{len(whole):,}')
                    st.dataframe(filter_catalog(whole,st.text_input('Filter EOD symbol',key='eod_filter'),limit=300),use_container_width=True,hide_index=True)
                    st.download_button('Export parsed EOD snapshot',whole.to_csv(index=False),file_name='eod_snapshot_parsed.csv',mime='text/csv')
                    st.warning('End-of-day snapshot, NOT a live quote or full technical backtest. Verify report date and corporate actions.')
                except ValueError as exc:st.error(str(exc))