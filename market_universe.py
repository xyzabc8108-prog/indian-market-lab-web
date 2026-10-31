"""NSE instrument directory and transparent paper-replay utilities.

The exchange's EQUITY_L.csv describes listed symbols, NOT a licensed live feed.
No broker credentials or order APIs are used by this module.
"""
from __future__ import annotations

import csv
import io
import math
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

EQUITY_URL = 'https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv'
NSE_LIST_PAGE = 'https://www.nseindia.com/static/market-data/securities-available-for-trading'
NSE_INDICES_PAGE = 'https://www.nseindia.com/market-data/live-market-indices'
IST = ZoneInfo('Asia/Kolkata')
SYMBOL_PATTERN = re.compile(r'^[A-Z0-9][A-Z0-9&._-]{0,24}$')

# An emergency directory, not represented as all NSE listings.
SEED_STOCKS = [
 ('RELIANCE','Reliance Industries'),('TCS','Tata Consultancy Services'),
 ('INFY','Infosys'),('HDFCBANK','HDFC Bank'),('ICICIBANK','ICICI Bank'),
 ('SBIN','State Bank of India'),('BHARTIARTL','Bharti Airtel'),
 ('ITC','ITC'),('HINDUNILVR','Hindustan Unilever'),('LT','Larsen & Toubro'),
 ('AXISBANK','Axis Bank'),('KOTAKBANK','Kotak Mahindra Bank'),
 ('BAJFINANCE','Bajaj Finance'),('BAJAJFINSV','Bajaj Finserv'),
 ('MARUTI','Maruti Suzuki India'),('M&M','Mahindra & Mahindra'),
 ('TATAMOTORS','Tata Motors'),('TATASTEEL','Tata Steel'),
 ('TITAN','Titan Company'),('WIPRO','Wipro'),('HCLTECH','HCL Technologies'),
 ('SUNPHARMA','Sun Pharmaceutical Industries'),('DRREDDY','Dr. Reddy’s Laboratories'),
 ('CIPLA','Cipla'),('NTPC','NTPC'),('POWERGRID','Power Grid Corporation'),
 ('ONGC','Oil and Natural Gas Corporation'),('COALINDIA','Coal India'),
 ('ADANIENT','Adani Enterprises'),('ADANIPORTS','Adani Ports'),
 ('ULTRACEMCO','UltraTech Cement'),('ASIANPAINT','Asian Paints'),
 ('EICHERMOT','Eicher Motors'),('NESTLEIND','Nestle India'),
 ('JSWSTEEL','JSW Steel'),('HINDALCO','Hindalco Industries'),
 ('BEL','Bharat Electronics'),('HAL','Hindustan Aeronautics'),
 ('INDIGO','InterGlobe Aviation'),('DMART','Avenue Supermarts'),
 ('TRENT','Trent'),('ZOMATO','Eternal (formerly Zomato)'),
 ('IRCTC','IRCTC'),('IRFC','Indian Railway Finance Corporation'),
 ('PFC','Power Finance Corporation'),('RECLTD','REC'),
 ('VEDL','Vedanta'),('DLF','DLF'),('GAIL','GAIL India'),
 ('PIDILITIND','Pidilite Industries'),('BRITANNIA','Britannia Industries'),
 ('DIVISLAB','Divi’s Laboratories'),('APOLLOHOSP','Apollo Hospitals'),
 ('TECHM','Tech Mahindra'),('GRASIM','Grasim Industries'),('JIOFIN','Jio Financial Services'),
]

# Index names are directory entries. Only a small set of Yahoo mappings is known;
# price lookup may still fail, and provider mappings must not be guessed.
INDEX_DEFINITIONS = [
 ('NIFTY 50','Broad market','^NSEI'),
 ('NIFTY NEXT 50','Broad market',None),
 ('NIFTY 100','Broad market',None),
 ('NIFTY 200','Broad market',None),
 ('NIFTY 500','Broad market',None),
 ('NIFTY BANK','Banking','^NSEBANK'),
 ('NIFTY FINANCIAL SERVICES','Financials',None),
 ('NIFTY PRIVATE BANK','Banking',None),
 ('NIFTY PSU BANK','Banking',None),
 ('NIFTY MIDCAP 50','Midcap',None),
 ('NIFTY MIDCAP 100','Midcap',None),
 ('NIFTY MIDCAP 150','Midcap',None),
 ('NIFTY MIDCAP SELECT','Midcap',None),
 ('NIFTY SMALLCAP 50','Smallcap',None),
 ('NIFTY SMALLCAP 100','Smallcap',None),
 ('NIFTY SMALLCAP 250','Smallcap',None),
 ('NIFTY AUTO','Sectoral',None),
 ('NIFTY IT','Sectoral','^CNXIT'),
 ('NIFTY FMCG','Sectoral',None),
 ('NIFTY PHARMA','Sectoral',None),
 ('NIFTY METAL','Sectoral',None),
 ('NIFTY REALTY','Sectoral',None),
 ('NIFTY MEDIA','Sectoral',None),
 ('NIFTY ENERGY','Sectoral',None),
 ('NIFTY OIL & GAS','Sectoral',None),
 ('NIFTY HEALTHCARE INDEX','Sectoral',None),
 ('NIFTY CONSUMER DURABLES','Sectoral',None),
 ('NIFTY INDIA DEFENCE','Thematic',None),
 ('NIFTY INDIA DIGITAL','Thematic',None),
 ('NIFTY INDIA MANUFACTURING','Thematic',None),
 ('NIFTY INFRASTRUCTURE','Thematic',None),
 ('NIFTY PSE','Thematic',None),
 ('NIFTY CPSE','Thematic',None),
 ('NIFTY COMMODITIES','Thematic',None),
 ('NIFTY 50 VALUE 20','Strategy',None),
 ('NIFTY 100 LOW VOLATILITY 30','Strategy',None),
 ('NIFTY 200 MOMENTUM 30','Strategy',None),
 ('NIFTY DIVIDEND OPPORTUNITIES 50','Strategy',None),
]


def _decode_csv(raw: bytes) -> list[dict]:
    if not raw or len(raw)>8_000_000:
        raise ValueError('Empty or oversized instrument CSV (maximum 8 MB).')
    try:
        content=raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        content=raw.decode('cp1252')
    reader=csv.DictReader(io.StringIO(content))
    if not reader.fieldnames:
        raise ValueError('CSV has no column headings')
    return [{str(k or '').strip().upper(): str(v or '').strip() for k,v in row.items()}
            for row in reader]


def load_equity_csv(raw: bytes) -> pd.DataFrame:
    """Parse an official NSE EQUITY_L.csv (or file with corresponding columns)."""
    rows=_decode_csv(raw)
    if not rows or not {'SYMBOL','NAME OF COMPANY','SERIES'}.issubset(rows[0]):
        raise ValueError('Expected NSE equity CSV columns: SYMBOL, NAME OF COMPANY, SERIES')
    clean=[]; seen=set()
    for r in rows:
        symbol=r['SYMBOL'].upper().strip(); series=r['SERIES'].upper().strip()
        if not SYMBOL_PATTERN.fullmatch(symbol) or series not in {'EQ','BE','BZ','SM','ST'}:
            continue
        key=(symbol,series)
        if key in seen:continue
        seen.add(key)
        clean.append({'Symbol':symbol,'Company':r['NAME OF COMPANY'][:180],
                      'Series':series,'Provider ticker':symbol+'.NS'})
    if not clean:raise ValueError('No recognized tradable symbols in CSV')
    return pd.DataFrame(clean).sort_values(['Symbol','Series']).reset_index(drop=True)


def fallback_equities() -> pd.DataFrame:
    return pd.DataFrame([{'Symbol':a,'Company':b,'Series':'EQ','Provider ticker':a+'.NS'}
                         for a,b in SEED_STOCKS])


def indices_table() -> pd.DataFrame:
    return pd.DataFrame([{'Index':name,'Group':group,'Yahoo ticker':y or '',
                          'Price mapped':bool(y)} for name,group,y in INDEX_DEFINITIONS])


def load_index_csv(raw: bytes) -> pd.DataFrame:
    """User imported index directory. Quote mapping is optional; no ticker inference."""
    rows=_decode_csv(raw)
    if not rows or not any(k in rows[0] for k in ('INDEX','INDEX NAME','INDEX_NAME','NAME')):
        raise ValueError('Index CSV must contain Index, Index Name, or Name column.')
    out=[];seen=set()
    for r in rows:
        name=next((r[k] for k in ('INDEX','INDEX NAME','INDEX_NAME','NAME') if r.get(k)), '').strip().upper()
        if not name or name in seen:continue
        seen.add(name)
        ticker=(r.get('YAHOO TICKER') or r.get('YAHOO_SYMBOL') or r.get('PROVIDER TICKER') or '').strip().upper()
        if ticker and not re.fullmatch(r'[\^A-Z0-9&._-]{2,30}',ticker):ticker=''
        out.append({'Index':name[:120],'Group':r.get('GROUP','Uploaded'),
                    'Yahoo ticker':ticker,'Price mapped':bool(ticker)})
    if not out:raise ValueError('No recognized index names in CSV.')
    return pd.DataFrame(out)


def filter_catalog(df:pd.DataFrame,search:str='',limit:int=150)->pd.DataFrame:
    query=search.strip()
    if not query:return df.head(limit)
    columns=[c for c in ('Symbol','Company','Index','Group') if c in df.columns]
    if not columns:return df.head(0)
    matched=pd.Series(False,index=df.index)
    for c in columns:matched|=df[c].astype(str).str.contains(query,case=False,regex=False,na=False)
    return df.loc[matched].head(limit)


def quote_age_minutes(bar_time, now:datetime|None=None)->float:
    instant=pd.Timestamp(bar_time)
    if instant.tzinfo is None: raise ValueError('Quote timestamp missing timezone')
    moment=now or datetime.now(IST)
    if moment.tzinfo is None: raise ValueError('Current time missing timezone')
    return max(0.,(moment-instant.to_pydatetime()).total_seconds()/60)


def paper_replay(candles:pd.DataFrame,entry_index:int,through_index:int,
                 quantity:int,stop:float,target:float)->dict:
    """Replay only historical bars revealed to this point; no future information.

    Conservative stop priority if both barriers occur in one bar (unresolvable without ticks).
    Explicitly labels gap/filled-price assumptions; not for real execution.
    """
    if not {'open','high','low','close'}.issubset(candles.columns):
        raise ValueError('Candles require open, high, low and close')
    if len(candles)<3 or not (0<=entry_index<through_index<len(candles)):
        raise ValueError('Replay entry and cursor are out of range')
    if quantity<1 or not math.isfinite(stop) or not math.isfinite(target):
        raise ValueError('Invalid paper position')
    entry=float(candles.iloc[entry_index]['close'])
    if not (0<stop<entry<target): raise ValueError('Require stop < prior-close entry < target')
    status='OPEN'; exit_price=float(candles.iloc[through_index]['close'])
    exit_index=through_index; ambiguous=False; gap=False
    for i in range(entry_index+1,through_index+1):
        r=candles.iloc[i]; low=float(r['low']);high=float(r['high']);op=float(r['open'])
        if op<=stop:
            status='STOP GAP';exit_price=op;exit_index=i;gap=True;break
        if op>=target:
            status='TARGET GAP';exit_price=op;exit_index=i;gap=True;break
        if low<=stop and high>=target:
            status='BOTH HIT — ASSUMED STOP';exit_price=stop;exit_index=i;ambiguous=True;break
        if low<=stop:
            status='STOP HIT';exit_price=stop;exit_index=i;break
        if high>=target:
            status='TARGET HIT';exit_price=target;exit_index=i;break
    return {'entry':entry,'exit_ref':exit_price,'quantity':quantity,
            'status':status,'pnl_before_costs':round(quantity*(exit_price-entry),2),
            'entry_bar':entry_index,'exit_bar':exit_index,
            'intrabar_ambiguous':ambiguous,'gap_assumption':gap}