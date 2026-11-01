"""NSE cash equity historical full-market scanner; research-only, no order execution."""
from __future__ import annotations
import io, math, re, zipfile
from pathlib import PurePosixPath
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd

IST = ZoneInfo("Asia/Kolkata")
MIN_SESSIONS = 60
MAX_INPUT_BYTES = 35 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 125 * 1024 * 1024
MAX_MEMBERS = 160
MAX_ROWS = 1_500_000
ALIASES = {
 "symbol":["SYMBOL","TCKRSYMB","TICKER","SECURITY","SECURITYID"],
 "series":["SERIES","SCTYSRS","SCTY SERIES"],
 "date":["DATE","TRADEDATE","TRADDT","TIMESTAMP","TRADINGDATE","TRDDT","DATEOFTRADING"],
 "open":["OPEN","OPENPRICE","OPNPRIC","OPNPRICE"],
 "high":["HIGH","HIGHPRICE","HGHPRIC","HGHPRICE"],
 "low":["LOW","LOWPRICE","LWPRIC","LWPRICE"],
 "close":["CLOSE","CLOSEPRICE","CLSPRIC","CLSPRC","CLS PRICE"],
 "volume":["VOLUME","TTLTRDQNTY","TOTTRDQTY","TOTALTRADEDQUANTITY","TTLTRADGVOL","TTLTRDQTY","TOTTRADEDQTY"]
}
def _norm(name):
    return re.sub(r"[^A-Z0-9]","",str(name).upper())
def _columns(df):
    found={_norm(c):c for c in df.columns}
    return {key: next((found[_norm(k)] for k in vals if _norm(k) in found),None)
            for key,vals in ALIASES.items()}
def _file_date(name):
    m=re.search(r"(?<!\d)(20\d{6})(?!\d)",name)
    if not m:return None
    val=pd.to_datetime(m.group(1),format="%Y%m%d",errors="coerce")
    return None if pd.isna(val) else val

def parse_daily_csv(raw:bytes,filename="history.csv"):
    if not raw or len(raw)>MAX_INPUT_BYTES:
        raise ValueError("CSV is empty or exceeds 35MB")
    try:df=pd.read_csv(io.BytesIO(raw),low_memory=False,encoding="utf-8-sig")
    except UnicodeDecodeError:df=pd.read_csv(io.BytesIO(raw),low_memory=False,encoding="cp1252")
    except Exception as exc:raise ValueError("Cannot read CSV") from exc
    if df.empty:raise ValueError("CSV has no data")
    cols=_columns(df)
    missing=[n for n in ("symbol","open","high","low","close","volume") if cols[n] is None]
    if missing:raise ValueError("Missing fields: "+", ".join(missing))
    if cols["date"] is None:
        d=_file_date(filename)
        if d is None:raise ValueError("Trading date is missing; filename must include YYYYMMDD")
        dates=pd.Series(d,index=df.index)
    else:
        dates=pd.to_datetime(df[cols["date"]],format="mixed",errors="coerce")
        if getattr(dates.dt,"tz",None) is not None:
            dates=dates.dt.tz_convert(IST).dt.tz_localize(None)
    out=pd.DataFrame({"date":dates,"symbol":df[cols["symbol"]].astype("string").str.strip().str.upper()})
    if cols["series"] is not None:
        mask=df[cols["series"]].astype("string").str.upper().str.strip().eq("EQ").fillna(False)
        out=out[mask].copy()
    for col in ("open","high","low","close","volume"):
        out[col]=pd.to_numeric(df.loc[out.index,cols[col]],errors="coerce")
    out=out.dropna(subset=["date","symbol","open","high","low","close","volume"])
    out["date"]=pd.to_datetime(out["date"],errors="coerce").dt.normalize()
    symbols=out.symbol.str.fullmatch(r"[A-Z0-9][A-Z0-9&._-]{0,25}").fillna(False)
    prices=(out[["open","high","low","close"]]>0).all(axis=1)
    ohlc=(out.high>=out[["open","low","close"]].max(axis=1))&(out.low<=out[["open","high","close"]].min(axis=1))
    valid=(symbols&prices&ohlc&(out.volume>=0)&np.isfinite(out.volume)&out.date.notna()&
           (out.date<=pd.Timestamp.now(tz=IST).tz_localize(None).normalize()))
    out=out[valid].copy()
    if out.empty:raise ValueError("No valid EQ cash-equity OHLCV rows")
    return out[["date","symbol","open","high","low","close","volume"]].reset_index(drop=True)

def parse_price_uploads(files):
    """Read user-provided multiple daily NSE CSV/ZIP, validate and dedupe."""
    if not files:raise ValueError("Upload daily OHLCV CSV/ZIP data first")
    parts=[];errors=[];total=0;parsed=0
    for name,raw in files:
        if not raw or len(raw)>MAX_INPUT_BYTES:
            errors.append(f"{name}: empty or over 35MB");continue
        payloads=[]
        if name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    members=[m for m in z.infolist() if not m.is_dir() and m.filename.lower().endswith(".csv")]
                    if len(members)>MAX_MEMBERS or sum(m.file_size for m in members)>MAX_TOTAL_UNCOMPRESSED:
                        raise ValueError("ZIP too large")
                    for m in members:
                        if m.file_size>MAX_INPUT_BYTES:raise ValueError("ZIP CSV over 35MB")
                        payloads.append((PurePosixPath(m.filename.replace("\\","/")).name,z.read(m)))
            except (zipfile.BadZipFile,zipfile.LargeZipFile,ValueError) as exc:
                errors.append(f"{name}: {exc}");continue
        elif name.lower().endswith(".csv"):payloads=[(name,raw)]
        else:errors.append(f"{name}: unsupported extension");continue
        for subname,body in payloads:
            total+=len(body)
            if total>MAX_TOTAL_UNCOMPRESSED:raise ValueError("Expanded CSV total >125MB")
            try:parts.append(parse_daily_csv(body,subname));parsed+=1
            except (ValueError,TypeError,OverflowError) as exc:errors.append(f"{subname}: {exc}")
    if not parts:raise ValueError("No valid price data. "+"; ".join(errors[:4]))
    full=pd.concat(parts,ignore_index=True)
    if len(full)>MAX_ROWS:raise ValueError("More than 1.5 million price rows")
    groups=full.groupby(["symbol","date"],sort=False)[["open","high","low","close","volume"]].nunique(dropna=False)
    conflicts=groups.gt(1).any(axis=1)
    bad_keys=conflicts[conflicts].index
    if len(bad_keys):
        idx=pd.MultiIndex.from_frame(full[["symbol","date"]])
        full=full.loc[~idx.isin(bad_keys)].copy()
    full=full.drop_duplicates(["symbol","date"]).sort_values(["symbol","date"]).reset_index(drop=True)
    if full.empty:raise ValueError("All prices are conflicting duplicates")
    quality={"Files parsed":parsed,"Files skipped":len(errors),"Skipped details":errors[:20],
             "Conflicting symbol-dates dropped":len(bad_keys),
             "Price rows":len(full),"Symbols with some data":full.symbol.nunique(),
             "First date":full.date.min().strftime("%Y-%m-%d"),
             "Last date":full.date.max().strftime("%Y-%m-%d")}
    return full,quality

def scan_market(prices,universe=None,capital=50_000,risk_pct=1.,allocation_pct=25.,min_turnover=2_000_000):
    """Rank dated historical indicator facts and size long-only hypothetical cash positions.
    Score is not a predicted probability. No future bars, no exchange orders.
    """
    if not all(math.isfinite(x) for x in (capital,risk_pct,allocation_pct,min_turnover)):
        raise ValueError("Finite budget values required")
    if not(capital>=1000 and 0<risk_pct<=5 and 0<allocation_pct<=100 and min_turnover>=0):
        raise ValueError("Invalid budget or risk limits")
    if prices.empty:raise ValueError("No price history provided")
    snapshot=pd.Timestamp(prices.date.max())
    allowed=None;names={}
    if universe is not None and not universe.empty:
        u=universe.copy()
        if "Asset type" in u:u=u[u["Asset type"].isin(["Mainboard equity","SME equity"])]
        if "Series" in u:u=u[u.Series.astype(str).str.upper().eq("EQ")]
        allowed=set(u.Symbol.astype(str).str.upper())
        if "Company" in u:names=dict(zip(u.Symbol.astype(str).str.upper(),u.Company.astype(str)))
    result=[];short=0;stale=0
    for symbol,g in prices.groupby("symbol",sort=False):
        if allowed is not None and symbol not in allowed:continue
        g=g.sort_values("date").reset_index(drop=True)
        if len(g)<MIN_SESSIONS:short+=1;continue
        latest=g.iloc[-1]
        if (snapshot-pd.Timestamp(latest.date)).days>7:stale+=1;continue
        close=g.close.astype(float);high=g.high.astype(float);low=g.low.astype(float);vol=g.volume.astype(float)
        sma20=float(close.tail(20).mean());sma50=float(close.tail(50).mean())
        tr=pd.concat([high-low,(high-close.shift()).abs(),(low-close.shift()).abs()],axis=1).max(axis=1)
        atr=float(tr.tail(14).mean())
        delta=close.diff();gain=delta.clip(lower=0).tail(14).mean();loss=(-delta.clip(upper=0)).tail(14).mean()
        rsi=100. if loss==0 and gain>0 else (50. if loss==0 else 100-100/(1+gain/loss))
        p=float(close.iloc[-1]);prior_high=float(high.iloc[-21:-1].max())
        avgvolume=float(vol.tail(20).mean());rel_volume=float(vol.iloc[-1]/avgvolume) if avgvolume>0 else 0.
        rupee_turnover=p*avgvolume;ret20=(p/float(close.iloc[-21])-1)*100
        trend=25 if p>sma20>sma50 else (12 if p>sma20 else 0)
        momentum=20 if ret20>=5 else (10 if ret20>0 else 0)
        liquidity=15 if rupee_turnover>=20_000_000 else (8 if rupee_turnover>=min_turnover else 0)
        rsi_score=10 if 45<=rsi<=70 else (5 if 40<=rsi<45 or 70<rsi<=80 else 0)
        breakout=15 if p>prior_high else (8 if p>=.97*prior_high else 0)
        volume=15 if rel_volume>=1.5 else (8 if rel_volume>=1 else 0)
        score=trend+momentum+liquidity+rsi_score+breakout+volume
        stop=p-2*atr;target=p+2*(p-stop)
        shares=(min(math.floor(capital*risk_pct/100/(p-stop)),math.floor(capital*allocation_pct/100/p))
                if atr>0 and stop>0 and p>stop else 0)
        reasons=[];risks=[]
        if trend==25:reasons.append("Close > SMA20 > SMA50")
        elif p<sma20:risks.append("Below SMA20")
        if ret20>0:reasons.append("Positive trailing 20-session momentum")
        else:risks.append("Non-positive 20-session return")
        if breakout==15:reasons.append("Broke preceding 20-session high")
        if rel_volume>=1.5:reasons.append("Volume >1.5x 20-session average")
        if rsi>80:risks.append("RSI >80 (possibly extended)")
        if rsi<40:risks.append("RSI <40 (weak momentum)")
        if rupee_turnover<min_turnover:risks.append("Below configured liquidity threshold")
        if shares<1:risks.append("Risk or allocation budget cannot fit a share")
        if atr<=0:risks.append("Non-positive ATR")
        status=("REVIEW CANDIDATE" if score>=65 and rupee_turnover>=min_turnover and shares>0
                and p>sma20 and ret20>0 else "WATCH / NO PAPER ENTRY")
        result.append({
         "Symbol":symbol,"Company":names.get(symbol,""),"Last date":latest.date,
         "Bars":len(g),"Last close ₹":round(p,2),"SMA20 ₹":round(sma20,2),
         "SMA50 ₹":round(sma50,2),"ATR14 ₹":round(atr,2),"RSI14":round(rsi,1),
         "20d return %":round(ret20,2),"Rel volume":round(rel_volume,2),
         "Avg turnover ₹":round(rupee_turnover,0),"20d prior high ₹":round(prior_high,2),
         "Score /100":int(score),"Trend /25":trend,"Momentum /20":momentum,
         "Liquidity /15":liquidity,"RSI /10":rsi_score,"Breakout /15":breakout,"Volume /15":volume,
         "Status":status,"Paper entry ref ₹":round(p,2),
         "Paper stop ref ₹":round(stop,2) if shares>0 else None,
         "Paper 2R target ₹":round(target,2) if shares>0 else None,
         "Paper shares":int(shares),"Paper allocated ₹":round(shares*p,2),
         "Max planned loss ₹":round(shares*(p-stop),2),
         "Reasons":" | ".join(reasons),"Risks":" | ".join(risks)})
    ranked=pd.DataFrame(result)
    if not ranked.empty:
        ranked=ranked.sort_values(["Score /100","Avg turnover ₹","Symbol"],
                                  ascending=[False,False,True]).reset_index(drop=True)
    summary={
     "Universe size":len(allowed) if allowed is not None else None,
     "Symbols in price file":prices.symbol.nunique(),
     "Symbols with >=60 sessions and recent bars":len(ranked),
     "Insufficient history":short,"Missing recent bars":stale,
     "Latest market date in upload":snapshot.strftime("%Y-%m-%d"),
     "File age days":(pd.Timestamp.now(tz=IST).tz_localize(None).normalize()-snapshot).days,
     "Cash capital ₹":capital,"Risk per idea ₹":capital*risk_pct/100,
     "Max per-position cash ₹":capital*allocation_pct/100,
     "Eligible candidates":int(ranked.Status.eq("REVIEW CANDIDATE").sum()) if not ranked.empty else 0}
    return ranked,summary
