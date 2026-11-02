"""Trader Terminal: descriptive candle patterns and illustrative path scenarios.

This research module does NOT forecast actual future prices or place orders.
"""
from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import json
import time

import numpy as np
import pandas as pd

IST = ZoneInfo("Asia/Kolkata")
CANDLE_RANGES = {
    "1m": ("1d", "5d"),
    "5m": ("1d", "5d"),
    "15m": ("1wk", "1mo"),
    "1h": ("1wk", "1mo"),
    "1d": ("3mo", "6mo", "1y"),
    "1wk": ("1y", "3y", "5y"),
}
TICKER = re.compile(r"^[A-Z0-9][A-Z0-9&.-]{0,24}$")
_CACHE: dict[tuple[str,str,str], tuple[float, pd.DataFrame]] = {}
MAX_CACHE = 150

PATTERN_LIBRARY = [
    ("Doji", "One candle", "Indecision"),
    ("Hammer", "One candle", "Potential bullish reversal"),
    ("Inverted Hammer", "One candle", "Potential bullish reversal"),
    ("Shooting Star", "One candle", "Potential bearish reversal"),
    ("Hanging Man", "One candle", "Potential bearish reversal"),
    ("Bullish Marubozu", "One candle", "Bullish pressure"),
    ("Bearish Marubozu", "One candle", "Bearish pressure"),
    ("Spinning Top", "One candle", "Indecision"),
    ("Bullish Engulfing", "Two candles", "Potential bullish reversal"),
    ("Bearish Engulfing", "Two candles", "Potential bearish reversal"),
    ("Bullish Harami", "Two candles", "Potential bullish reversal"),
    ("Bearish Harami", "Two candles", "Potential bearish reversal"),
    ("Piercing Line", "Two candles", "Potential bullish reversal"),
    ("Dark Cloud Cover", "Two candles", "Potential bearish reversal"),
    ("Tweezer Top", "Two candles", "Potential bearish reversal"),
    ("Tweezer Bottom", "Two candles", "Potential bullish reversal"),
    ("Morning Star", "Three candles", "Potential bullish reversal"),
    ("Evening Star", "Three candles", "Potential bearish reversal"),
    ("Three White Soldiers", "Three candles", "Bullish pressure"),
    ("Three Black Crows", "Three candles", "Bearish pressure"),
    ("Double Top", "Chart structure", "Potential bearish reversal"),
    ("Double Bottom", "Chart structure", "Potential bullish reversal"),
    ("Ascending Triangle", "Chart structure", "Potential bullish continuation"),
    ("Descending Triangle", "Chart structure", "Potential bearish continuation"),
    ("Symmetrical Triangle", "Chart structure", "Possible breakout in either direction"),
    ("Upward Channel", "Chart structure", "Trend"),
    ("Downward Channel", "Chart structure", "Trend"),
]
_KIND = {item[0]: (item[1], item[2]) for item in PATTERN_LIBRARY}


def normalize_ticker(value: str) -> str:
    value = str(value or "").strip().upper()
    if value.startswith("NSE:"): value = value[4:]
    if value.endswith(".NS"): value = value[:-3]
    if not TICKER.fullmatch(value):
        raise ValueError("Enter an NSE stock symbol such as RELIANCE, TCS or INFY.")
    return value + ".NS"


def validate_candles(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise ValueError("Price history is empty.")
    required = ("time", "open", "high", "low", "close", "volume")
    if not all(c in frame.columns for c in required):
        raise ValueError("Price history is missing required columns.")
    d = frame.loc[:, required].copy()
    d["time"] = pd.to_datetime(d["time"], errors="coerce", utc=True)
    for col in required[1:]:
        d[col] = pd.to_numeric(d[col], errors="coerce")
    d = d.replace([np.inf, -np.inf], np.nan)
    d = d.dropna(subset=["time","open","high","low","close"])
    d["volume"] = d["volume"].fillna(0).clip(lower=0)
    d = d[
        (d["open"] > 0) & (d["close"] > 0) & (d["low"] > 0)
        & (d["high"] >= d[["open","close","low"]].max(axis=1))
        & (d["low"] <= d[["open","close"]].min(axis=1))
    ]
    d = d.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    if len(d) < 25:
        raise ValueError("At least 25 valid candles are required for this terminal.")
    return d


def fetch_candles(ticker: str, interval: str, lookback: str) -> pd.DataFrame:
    if interval not in CANDLE_RANGES or lookback not in CANDLE_RANGES[interval]:
        raise ValueError("This candle interval and history range are not supported together.")
    ticker = normalize_ticker(ticker)
    key = ticker, interval, lookback
    cached = _CACHE.get(key)
    now = time.monotonic()
    if cached and cached[0] > now:
        return cached[1].copy()
    # The provider accepts 5d/1mo/5y, not every human-friendly range.
    # Fetch a compatible envelope and trim to the requested calendar period.
    provider_range = {"1wk": "1mo", "3y": "5y"}.get(lookback, lookback)
    uri = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + quote(ticker, safe=".")
           + "?interval=" + interval + "&range=" + provider_range)
    req = Request(uri, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=12) as response:
            payload = json.load(response)
        entry = payload["chart"]["result"][0]
        bars = entry["indicators"]["quote"][0]
        frame = pd.DataFrame({
            "time": pd.to_datetime(entry["timestamp"], unit="s", utc=True),
            "open": bars["open"], "high": bars["high"],
            "low": bars["low"], "close": bars["close"],
            "volume": bars["volume"],
        })
        if lookback in ("1wk", "3y"):
            from pandas import Timedelta
            from pandas import Timestamp
            days = 7 if lookback == "1wk" else 365 * 3 + 1
            cutoff = Timestamp.now(tz="UTC") - Timedelta(days=days)
            frame = frame.loc[frame["time"] >= cutoff].copy()
        frame = validate_candles(frame)
    except (TimeoutError, HTTPError, URLError, OSError, ValueError,
            TypeError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise ValueError("Historical candles are currently unavailable for that symbol and interval.") from exc
    if len(_CACHE) >= MAX_CACHE:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = (now + (60 if interval in ("1m","5m","15m","1h") else 300), frame.copy())
    return frame


def _pattern(name, explanation, time_iso):
    category, tendency = _KIND[name]
    return {"name": name, "category": category, "tendency": tendency,
            "reason": explanation, "time": time_iso, "confirmed": False}


def detect_patterns(frame: pd.DataFrame) -> list[dict]:
    """Rule-based geometric candidates, NOT validated predictive signals."""
    d = validate_candles(frame)
    o = d.open.to_numpy(float); h = d.high.to_numpy(float)
    l = d.low.to_numpy(float); c = d.close.to_numpy(float)
    n=len(d); patterns=[]
    # Evaluate the latest five candles for short-lived formations.
    for i in range(max(1,n-5),n):
        body=abs(c[i]-o[i]); span=max(1e-9,h[i]-l[i])
        upper=h[i]-max(o[i],c[i]); lower=min(o[i],c[i])-l[i]
        prev_body=abs(c[i-1]-o[i-1])
        ts=d.time.iloc[i].isoformat()
        if body/span<=0.10: patterns.append(_pattern("Doji","Open and close are nearly equal.",ts))
        if .10<body/span<=.27 and min(upper,lower)>=body:
            patterns.append(_pattern("Spinning Top","Small real body with shadows on both sides.",ts))
        if body/span>=.85:
            name="Bullish Marubozu" if c[i]>o[i] else "Bearish Marubozu"
            patterns.append(_pattern(name,"Large candle body occupies most of the candle range.",ts))
        if body>0 and lower>=2*body and upper<=body*.8:
            name="Hammer" if c[i-1]<o[i-1] else "Hanging Man"
            patterns.append(_pattern(name,"Long lower shadow with a small upper shadow.",ts))
        if body>0 and upper>=2*body and lower<=body*.8:
            name="Inverted Hammer" if c[i-1]<o[i-1] else "Shooting Star"
            patterns.append(_pattern(name,"Long upper shadow with a small lower shadow.",ts))
        if c[i-1]<o[i-1] and c[i]>o[i] and o[i]<=c[i-1] and c[i]>=o[i-1] and body>0:
            patterns.append(_pattern("Bullish Engulfing","Up candle body covers the prior down candle body.",ts))
        if c[i-1]>o[i-1] and c[i]<o[i] and o[i]>=c[i-1] and c[i]<=o[i-1] and body>0:
            patterns.append(_pattern("Bearish Engulfing","Down candle body covers the prior up candle body.",ts))
        inside=min(o[i],c[i])>=min(o[i-1],c[i-1]) and max(o[i],c[i])<=max(o[i-1],c[i-1])
        if inside and body<prev_body*.60:
            name="Bullish Harami" if c[i-1]<o[i-1] else "Bearish Harami"
            patterns.append(_pattern(name,"A smaller candle body sits within the prior candle's body.",ts))
        if c[i-1]<o[i-1] and c[i]>o[i] and c[i]>(o[i-1]+c[i-1])/2 and c[i]<o[i-1] and o[i]<c[i-1]:
            patterns.append(_pattern("Piercing Line","Up candle recovers over half of the prior down candle.",ts))
        if c[i-1]>o[i-1] and c[i]<o[i] and c[i]<(o[i-1]+c[i-1])/2 and c[i]>o[i-1] and o[i]>c[i-1]:
            patterns.append(_pattern("Dark Cloud Cover","Down candle retraces over half of the prior up candle.",ts))
        if abs(h[i]-h[i-1])/span<.08 and c[i-1]>o[i-1] and c[i]<o[i]:
            patterns.append(_pattern("Tweezer Top","Similar nearby highs across an up and down candle.",ts))
        if abs(l[i]-l[i-1])/span<.08 and c[i-1]<o[i-1] and c[i]>o[i]:
            patterns.append(_pattern("Tweezer Bottom","Similar nearby lows across a down and up candle.",ts))
        if i>=2:
            first,mid,last=i-2,i-1,i
            if c[first]<o[first] and abs(c[mid]-o[mid])<abs(c[first]-o[first])*.45 and c[last]>o[last] and c[last]>(o[first]+c[first])/2:
                patterns.append(_pattern("Morning Star","Down candle, smaller body, then stronger up candle.",ts))
            if c[first]>o[first] and abs(c[mid]-o[mid])<abs(c[first]-o[first])*.45 and c[last]<o[last] and c[last]<(o[first]+c[first])/2:
                patterns.append(_pattern("Evening Star","Up candle, smaller body, then stronger down candle.",ts))
            if all(c[j]>o[j] for j in (first,mid,last)) and c[first]<c[mid]<c[last]:
                patterns.append(_pattern("Three White Soldiers","Three rising up candle closes.",ts))
            if all(c[j]<o[j] for j in (first,mid,last)) and c[first]>c[mid]>c[last]:
                patterns.append(_pattern("Three Black Crows","Three falling down candle closes.",ts))
    # Recent swing structure. Use only confirmed pivots (2 bars on each side).
    window=min(90,n)
    hh=h[-window:]; ll=l[-window:]
    highs=[(i,hh[i]) for i in range(2,window-2)
           if hh[i]>max(hh[i-1],hh[i-2],hh[i+1],hh[i+2])]
    lows=[(i,ll[i]) for i in range(2,window-2)
          if ll[i]<min(ll[i-1],ll[i-2],ll[i+1],ll[i+2])]
    last_ts=d.time.iloc[-1].isoformat()
    tol=max(float(np.mean(hh-ll))*1.8,float(c[-1])*.015)
    if len(highs)>=2:
        a,b=highs[-2:]
        if b[0]-a[0]>=4 and abs(b[1]-a[1])<=tol:
            patterns.append(_pattern("Double Top","Two recent swing highs are near the same price; a neckline break is not established.",last_ts))
    if len(lows)>=2:
        a,b=lows[-2:]
        if b[0]-a[0]>=4 and abs(b[1]-a[1])<=tol:
            patterns.append(_pattern("Double Bottom","Two recent swing lows are near the same price; a neckline break is not established.",last_ts))
    if n>=35:
        count=25
        highs25=h[-count:];lows25=l[-count:]
        x=np.arange(count,dtype=float)
        upper_slope=float(np.polyfit(x,highs25,1)[0])
        lower_slope=float(np.polyfit(x,lows25,1)[0])
        level=float(np.mean(c[-count:]))
        threshold=max(level*.0006,0.0001)
        horizontal=max(level*.0008,0.0001)
        if abs(upper_slope)<horizontal and lower_slope>threshold:
            patterns.append(_pattern("Ascending Triangle","Recent highs are broadly flat while lows rise.",last_ts))
        elif abs(lower_slope)<horizontal and upper_slope< -threshold:
            patterns.append(_pattern("Descending Triangle","Recent lows are broadly flat while highs decline.",last_ts))
        elif upper_slope< -threshold and lower_slope>threshold:
            patterns.append(_pattern("Symmetrical Triangle","Recent high trend slopes down while low trend slopes up.",last_ts))
        elif upper_slope>threshold and lower_slope>threshold:
            patterns.append(_pattern("Upward Channel","Recent high and low trendlines both rise.",last_ts))
        elif upper_slope< -threshold and lower_slope< -threshold:
            patterns.append(_pattern("Downward Channel","Recent high and low trendlines both decline.",last_ts))
    # Prioritize recent evidence without repeating a pattern type.
    patterns.sort(key=lambda x:x["time"],reverse=True)
    output=[];seen=set()
    for item in patterns:
        if item["name"] in seen:continue
        seen.add(item["name"]);output.append(item)
    return output[:16]


def scenario_report(frame: pd.DataFrame, horizon: int, seed_key: str) -> dict:
    """Bootstrap historical log-returns: scenario distribution, not a forecast."""
    d=validate_candles(frame)
    if not 1<=horizon<=40:
        raise ValueError("Future candle horizon must be between 1 and 40.")
    returns=d.close.pct_change().replace([np.inf,-np.inf],np.nan).dropna()
    if len(returns)<24 or (returns<=-1).any():
        raise ValueError("Insufficient valid returns for scenario modelling.")
    r=returns.clip(lower=-.80,upper=.80).to_numpy(float)
    seed=int.from_bytes(hashlib.sha256(seed_key.encode()).digest()[:8],"big") % (2**32)
    rng=np.random.default_rng(seed)
    n_paths=2500
    sampled=rng.choice(np.log1p(r[-min(250,len(r)):]),size=(n_paths,horizon),replace=True)
    anchor=float(d.close.iloc[-1])
    paths=anchor*np.exp(np.cumsum(sampled,axis=1))
    p10=np.percentile(paths,10,axis=0);p50=np.percentile(paths,50,axis=0);p90=np.percentile(paths,90,axis=0)
    positive=float((paths[:,-1]>anchor).mean())
    return {"horizon":horizon,"paths":n_paths,
            "anchor":round(anchor,2),
            "downside":round(float(p10[-1]),2),
            "middle":round(float(p50[-1]),2),
            "upside":round(float(p90[-1]),2),
            "modeled_above_reference_pct":round(positive*100,1),
            "bands":[{"step":i+1,"low":round(float(p10[i]),2),"mid":round(float(p50[i]),2),"high":round(float(p90[i]),2)} for i in range(horizon)],
            "method":"Historical daily/intraday log-return resampling; iid with replacement; excludes news, regime changes, fees and gaps. Values are NOT calibrated market probabilities or predictions."}


def terminal_report(symbol: str, interval: str, lookback: str, horizon: int) -> dict:
    ticker=normalize_ticker(symbol)
    d=fetch_candles(ticker,interval,lookback)
    c=d.close.astype(float)
    sma20=c.rolling(20,min_periods=20).mean()
    sma50=c.rolling(50,min_periods=50).mean()
    ema20=c.ewm(span=20,adjust=False).mean()
    last=d.iloc[-1]
    previous=d.iloc[-2]
    scenario=scenario_report(d,horizon,ticker+interval+lookback+str(last.time)+str(horizon))
    patterns=detect_patterns(d)
    time_last=pd.Timestamp(last.time)
    lag_seconds=max(0,(datetime.now(IST)-time_last.to_pydatetime().astimezone(IST)).total_seconds())
    bias="Bullish" if last.close>sma20.iloc[-1] and (len(d)<50 or sma20.iloc[-1]>sma50.iloc[-1]) else "Bearish" if last.close<sma20.iloc[-1] else "Sideways"
    return {
       "symbol":ticker,"interval":interval,"lookback":lookback,
       "latest_time":time_last.isoformat(),"bar_age_minutes":round(lag_seconds/60),
       "last_price":round(float(last.close),2),
       "change_pct":round((float(last.close)/float(previous.close)-1)*100,2),
       "trend":bias,"source":"Unofficial Yahoo Finance historical OHLC; delays and rate limits possible.",
       "bars":[{"time":int(pd.Timestamp(row.time).timestamp()),"open":round(float(row.open),4),
                "high":round(float(row.high),4),"low":round(float(row.low),4),
                "close":round(float(row.close),4),"volume":float(row.volume),
                "sma20":round(float(sma20.iloc[i]),4) if pd.notna(sma20.iloc[i]) else None,
                "sma50":round(float(sma50.iloc[i]),4) if pd.notna(sma50.iloc[i]) else None,
                "ema20":round(float(ema20.iloc[i]),4)}
               for i,row in enumerate(d.itertuples(index=False))][-1000:],
       "patterns":patterns,"pattern_library":[{"name":n,"category":cat,"tendency":trend} for n,cat,trend in PATTERN_LIBRARY],
       "scenario":scenario,
       "caveat":"Pattern matches are heuristic candidates, not confirmations or buy/sell signals. Scenarios are historical resamples, not reliable predictions. No real orders."
    }
