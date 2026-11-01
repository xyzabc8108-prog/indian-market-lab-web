"""Indian Market Lab — educational NSE research, no broker integration or orders."""
import json, math, random, re
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import quote
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st

IST=ZoneInfo("Asia/Kolkata")
PERIODS={"1d":["1mo","3mo","6mo","1y","2y","5y"],"5m":["1d","5d","1mo"],"15m":["1d","5d","1mo"]}
st.set_page_config(page_title="Indian Market Lab",page_icon="📊",layout="wide")
st.markdown("""<style>.stApp{background:linear-gradient(145deg,#081421,#0d2134)}
[data-testid="stMetric"]{background:#142b43;border:1px solid #29405c;padding:14px;border-radius:12px}
h1,h2,h3{letter-spacing:-.04em}</style>""",unsafe_allow_html=True)

def symbols_from(raw):
    out=[]
    for sym in re.split(r"[,;\s]+",raw.upper().strip()):
        if not sym:continue
        if sym.endswith(".NS"):sym=sym[:-3]
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9&-]{0,19}",sym):
            raise ValueError("Use NSE symbols such as RELIANCE, TCS or INFY")
        item=sym+".NS"
        if item not in out:out.append(item)
    if not 1<=len(out)<=8:raise ValueError("Enter between 1 and 8 NSE tickers")
    return out

@st.cache_data(ttl=240,show_spinner=False)
def history(symbol,interval,period,demo):
    if demo:
        seed=sum((i+1)*ord(c) for i,c in enumerate(symbol))
        rng=random.Random(seed)
        dates=pd.bdate_range(end=datetime.now(IST).date(),periods=240,tz="Asia/Kolkata")
        p=100+seed%500
        rows=[]
        for d in dates:
            op=p;p=max(1,op*(1+rng.uniform(-.021,.021)))
            rows.append((d,op,max(op,p)*1.004,min(op,p)*.996,p,rng.randint(100000,4000000)))
        return pd.DataFrame(rows,columns=["time","open","high","low","close","volume"]),"SYNTHETIC DEMO — not actual prices"
    if period not in PERIODS.get(interval,[]):raise ValueError("Unsupported interval/range")
    url="https://query1.finance.yahoo.com/v8/finance/chart/"+quote(symbol,safe=".")+"?range="+period+"&interval="+interval
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (Educational Research)","Accept":"application/json"})
    try:
        with urlopen(req,timeout=12) as resp:doc=json.load(resp)
        item=doc["chart"]["result"][0]
        times=pd.to_datetime(item["timestamp"],unit="s",utc=True).tz_convert("Asia/Kolkata")
        candles=item["indicators"]["quote"][0]
        df=pd.DataFrame({"time":times,"open":candles["open"],"high":candles["high"],
                         "low":candles["low"],"close":candles["close"],"volume":candles["volume"]})
        df=df.dropna(subset=["open","high","low","close"]).sort_values("time")
        df=df[(df["close"]>0)&(df["open"]>0)]
        if df.empty:raise ValueError("No valid bars returned")
        return df,"Unofficial Yahoo Finance research data — delay and freshness not verified"
    except (TimeoutError,HTTPError,URLError,ValueError,KeyError,TypeError,IndexError) as e:
        raise ValueError("Research data unavailable or rate-limited: "+str(e)) from e

def indicators(df):
    c=df["close"].astype(float)
    last=float(c.iloc[-1]);prev=float(c.iloc[-2]) if len(c)>1 else last
    avg=float(c.tail(20).mean()) if len(c)>=20 else None
    return {"price":round(last,2),"change":round((last/prev-1)*100,2),
            "ma20":round(avg,2) if avg else None,
            "flag":"Above MA20" if avg and last>avg else "Below MA20" if avg else "Insufficient bars",
            "time":df["time"].iloc[-1].strftime("%d %b %Y %I:%M %p IST")}

with st.sidebar:
    st.title("📈 Indian Market Lab")
    mode=st.radio("Data source for advanced tools",["Synthetic demo","Yahoo research data"],index=1)
    demo=mode=="Synthetic demo"
    raw=st.text_area("NSE watchlist","RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK",height=100)
    try:symbols=symbols_from(raw)
    except ValueError as e:st.error(str(e));st.stop()
    st.caption("Read-only • INR • IST • no broker login")
    if st.button("Clear provider cache"):history.clear()

st.title("Indian Market Lab")
st.caption("NSE watchlists, charts, research screens, hypothetical backtests, risk planning and paper notes.")
if demo:st.warning("Advanced tools are in DEMO mode: their prices are fabricated. Auto Stock Assistant independently requests research data, never demo quotes.")
else:st.info("Public unofficial research data may be stale, delayed, unavailable or rate-limited. Not verified real-time.")
st.caption("Dashboard time: "+datetime.now(IST).strftime("%d %b %Y · %I:%M %p IST"))
auto_tab,stock_tab,scenario_tab,budget_tab,fo_tab,news_tab,watch,charts,screen,backtest,risk,journal,guide,universe_tab,scanner_tab=st.tabs(["🔎 Auto Stock Assistant","Stock Decision Lab","Scenario Engine","Budget Desk","F&O Risk","News Radar","Watchlist","Charts & CSV","Screener","Backtest","Risk planner","Paper journal","Guide","All Stocks & Indices","Full-Market Scanner"])

with watch:
    st.subheader("NSE watchlist")
    if st.button("Load watchlist",type="primary"):
        rows=[]
        for s in symbols:
            try:
                df,origin=history(s,"1d","1mo",demo);m=indicators(df)
                rows.append({"Symbol":s,"Price ₹":m["price"],"Bar change %":m["change"],
                             "MA20 ₹":m["ma20"],"Flag":m["flag"],"Last bar IST":m["time"],"Source":origin})
            except ValueError as e:st.warning(s+": "+str(e))
        st.session_state.watch=(mode,rows)
    if "watch" in st.session_state:
        origin,rows=st.session_state.watch
        if origin!=mode:st.info("Refresh watchlist after changing data source")
        elif rows:
            st.dataframe(rows,use_container_width=True,hide_index=True)
            st.download_button("Download watchlist CSV",pd.DataFrame(rows).to_csv(index=False),"watchlist.csv","text/csv")

with charts:
    st.subheader("Historical price chart")
    a,b,c=st.columns(3)
    sym=a.selectbox("Stock",symbols,key="chart_sym")
    interval=b.selectbox("Interval",list(PERIODS))
    period=c.selectbox("Range",PERIODS[interval])
    if st.button("Show chart",type="primary"):
        try:df,origin=history(sym,interval,period,demo);st.session_state.chart=(mode,sym,interval,period,df,origin)
        except ValueError as e:st.error(str(e))
    if "chart" in st.session_state:
        src,s,iv,per,df,origin=st.session_state.chart
        if (src,s,iv,per)!=(mode,sym,interval,period):st.info("Click Show chart to refresh")
        else:
            m=indicators(df)
            st.metric("Last close ₹",f"₹{m['price']:,.2f}",f"{m['change']:+.2f}%")
            st.caption(origin+" | Last bar: "+m["time"])
            st.line_chart(df.set_index("time")[["close"]],height=340)
            st.bar_chart(df.set_index("time")[["volume"]],height=135)
            st.download_button("Download candles CSV",df.to_csv(index=False),"candles.csv","text/csv")

with screen:
    st.subheader("Simple daily-trend screener")
    st.caption("Descriptive moving-average flags — not buy or sell recommendations.")
    if st.button("Run screener",type="primary"):
        rows=[]
        for s in symbols:
            try:
                df,_=history(s,"1d","6mo",demo);m=indicators(df)
                rows.append({"Symbol":s,"Close ₹":m["price"],"Change %":m["change"],
                             "MA20 ₹":m["ma20"],"Flag":m["flag"],"Last bar":m["time"]})
            except ValueError as e:st.warning(s+": "+str(e))
        if rows:st.dataframe(pd.DataFrame(rows).sort_values("Change %",ascending=False),
                             use_container_width=True,hide_index=True)

with backtest:
    st.subheader("SMA paper strategy")
    st.caption("Prior-close SMA signal, next-open long/flat execution. Excludes taxes, slippage and gaps.")
    s=st.selectbox("Backtest stock",symbols)
    a,b,c=st.columns(3)
    short=a.number_input("Short SMA",2,60,5)
    long=b.number_input("Long SMA",3,150,20)
    cost=c.number_input("One-way cost (basis points)",0,200,10)
    if st.button("Run backtest",type="primary"):
        if short>=long:st.error("Short SMA must be shorter than long SMA")
        else:
            try:
                df,origin=history(s,"1d","2y",demo)
                o=df["open"].astype(float).reset_index(drop=True)
                close=df["close"].astype(float).reset_index(drop=True)
                signals=(close.rolling(short).mean()>close.rolling(long).mean()).fillna(False)
                equity=100000.0;prior=0;entries=0;rows=[]
                for i in range(1,len(df)-1):
                    pos=int(bool(signals.iloc[i-1]));entries+=int(pos==1 and prior==0)
                    growth=pos*(float(o.iloc[i+1])/float(o.iloc[i])-1)-abs(pos-prior)*cost/10000
                    equity*=max(0,1+growth);rows.append({"time":df["time"].iloc[i],"Equity ₹":equity})
                    prior=pos
                st.metric("Hypothetical ending equity",f"₹{equity:,.2f}",f"{(equity/100000-1)*100:+.2f}%")
                st.caption(f"₹100,000 initial capital • {entries} simulated entries • {origin}")
                st.line_chart(pd.DataFrame(rows).set_index("time"))
            except (ValueError,ZeroDivisionError) as e:st.error(str(e))

with risk:
    st.subheader("Hypothetical long-only position sizing")
    a,b,c=st.columns(3)
    capital=a.number_input("Capital ₹",min_value=1000.0,value=100000.0)
    risk_pct=b.number_input("Risk budget %",min_value=.1,max_value=10.0,value=1.0)
    cap_pct=c.number_input("Max position %",min_value=1.0,max_value=100.0,value=25.0)
    x,y,z=st.columns(3)
    entry=x.number_input("Entry ₹",min_value=.01,value=1000.0)
    stop=y.number_input("Stop ₹",min_value=.01,value=950.0)
    target=z.number_input("Target ₹",min_value=.01,value=1100.0)
    if stop>=entry or target<=entry:st.warning("Long example requires stop < entry < target")
    else:
        qty=max(0,min(math.floor(capital*risk_pct/100/(entry-stop)),
                      math.floor(capital*cap_pct/100/entry)))
        st.metric("Paper shares",qty)
        st.write(f"Planned loss **₹{qty*(entry-stop):,.2f}** · Potential gain **₹{qty*(target-entry):,.2f}**")
        st.caption("Assumes ideal fills; excludes slippage, taxes and brokerage fees")

with journal:
    st.subheader("Paper journal (session only)")
    if "paper_notes" not in st.session_state:st.session_state.paper_notes=[]
    with st.form("journal"):
        s=st.selectbox("Symbol",symbols)
        action=st.selectbox("Hypothetical action",["Observe","Paper buy","Paper sell"])
        note=st.text_input("Research note")
        if st.form_submit_button("Save paper note"):
            st.session_state.paper_notes.append({"Time IST":datetime.now(IST).isoformat(),
                                                 "Symbol":s,"Action":action,"Note":note})
            st.success("Saved only to this session")
    if st.session_state.paper_notes:
        st.dataframe(st.session_state.paper_notes,use_container_width=True,hide_index=True)
        st.download_button("Export journal CSV",
                           pd.DataFrame(st.session_state.paper_notes).to_csv(index=False),
                           "journal.csv","text/csv")
    st.caption("Notes are not permanent; export before leaving. No real orders are sent.")

with guide:
    st.subheader("Limitations and research guidance")
    st.write("Synthetic demo prices are **fabricated**. Yahoo research prices use an unofficial public chart endpoint and can be delayed, stale or blocked, especially from cloud hosting. No exchange-verified real-time feed is connected.")
    st.write("Backtests are hypothetical, use simplified costs, and cannot predict future results. Verify research data against NSE publications. This website never logs into a brokerage account or executes trades.")


# Advanced research views; all outputs are educational and non-executable.
from advanced_ui import render_features
render_features(stock_tab,scenario_tab,budget_tab,fo_tab,news_tab,history,mode,symbols)

# Search all listed NSE stocks; optional on-demand selected-price refresh/replay.
from universe_ui import render_universe
render_universe(universe_tab,history,mode)


# Phase 1 NSE market-wide EOD ranking (read-only, strict data validation).
from scanner_ui import render_full_market_scanner
render_full_market_scanner(scanner_tab)


# One-selection first-tab research. This never substitutes fabricated quotes.
from quick_stock_ui import render_auto_stock
render_auto_stock(auto_tab, history)
