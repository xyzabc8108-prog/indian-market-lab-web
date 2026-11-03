"""Read-only FastAPI backend; serves the modular frontend on the same origin.

No real orders, broker tokens, account data or public shared paper journals.
External historical prices are unofficial, can be delayed or blocked.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import json
import math
import re
import sys
import time

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from market_universe import fallback_equities, indices_table, load_equity_csv, EQUITY_URL
from full_market_scanner import parse_price_uploads, scan_market
from research_engine import technical_snapshot, position_budget, validate_ohlcv, option_long_budget, future_budget
from news_radar import read_public_headlines, OFFICIAL_LINKS
from fullstack.backend.third_party_safety import public_headline_feed_enabled, NEWS_FEED_PAUSED_NOTICE
from fullstack.backend.terminal_engine import terminal_report, CANDLE_RANGES
from fullstack.backend.beta import router as beta_router
from fullstack.backend.beta_admin import admin_router
from fullstack.backend.market_data_safety import (
    market_data_status, public_market_data_safety_mode,
    require_public_market_data,
)
from fullstack.backend.scanner_safety import (
    SCANNER_PAUSED_NOTICE, public_scanner_upload_enabled,
    public_scanner_status, synthetic_scanner_demonstration,
)

FRONTEND = Path(__file__).resolve().parents[1] / 'frontend'
IST = ZoneInfo('Asia/Kolkata')
SYMBOL = re.compile(r'^[A-Z0-9][A-Z0-9&.-]{0,24}$')
INDEX_TICKERS = {'^NSEI', '^NSEBANK', '^CNXIT'}
CACHE: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}
app = FastAPI(title='Indian Market Lab API', description='Educational NSE research; no orders or live feed guarantees.', version='2.0')
app.include_router(beta_router)
app.include_router(admin_router)

# Restrict browser resource execution without blocking the externally hosted
# Lightweight Charts library currently used by Trader Mode.
_SITE_CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "script-src 'self' https://unpkg.com; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self' data:; "
    "connect-src 'self'"
)

# FastAPI's stock Swagger/ReDoc pages need their documented CDN scripts
# and inline initialization. This narrower exception does not apply to
# any public beta or trader page.
_DOCS_CSP = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "object-src 'none'; "
    "frame-ancestors 'none'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com"
)


@app.middleware('http')
async def browser_security_headers(request: Request, call_next):
    # Refuse multipart uploads *before* parsing user price files in safe mode.
    if (request.url.path == '/api/scanner/import' and request.method == 'POST'
            and not public_scanner_upload_enabled()):
        response = JSONResponse(
            status_code=503, content={'detail': SCANNER_PAUSED_NOTICE}
        )
    else:
        response = await call_next(request)
    # Browsers ignore HSTS over plain HTTP (e.g., during local development).
    # Do not includeSubDomains on the shared onrender.com domain.
    response.headers['Strict-Transport-Security'] = 'max-age=31536000'
    response.headers['Content-Security-Policy'] = (
        _DOCS_CSP if request.url.path in ('/docs', '/redoc') else _SITE_CSP
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = (
        'camera=(), microphone=(), geolocation=(), payment=()'
    )
    if (request.url.path.startswith('/api/scanner/') or
        request.url.path.startswith('/api/stock/') or
        (request.url.path.startswith('/api/terminal/') and
         request.url.path not in ('/api/terminal/config', '/api/terminal/universe'))):
        response.headers['Cache-Control'] = 'no-store'
    return response


def normalize_ticker(value: str) -> str:
    text = str(value or '').strip().upper()
    if text in INDEX_TICKERS:
        return text
    if text.startswith('NSE:'):
        text = text[4:]
    if text.endswith('.NS'):
        text = text[:-3]
    if not SYMBOL.fullmatch(text):
        raise ValueError('Use a valid NSE stock ticker such as RELIANCE, INFY or TCS.')
    return text + '.NS'


def yahoo_history(ticker: str, period: str = '1y') -> pd.DataFrame:
    # Also block cache reuse or direct internal access when safety mode is active.
    if public_market_data_safety_mode():
        raise ValueError("Public market-price provider access is disabled pending data-rights review.")
    if period not in {'3mo', '6mo', '1y', '2y'}:
        raise ValueError('Unsupported price-history period')
    sym = normalize_ticker(ticker)
    key = (sym, period)
    now = time.monotonic()
    cached = CACHE.get(key)
    if cached and cached[0] > now:
        return cached[1].copy()
    uri = 'https://query1.finance.yahoo.com/v8/finance/chart/' + quote(sym, safe='.^') + '?interval=1d&range=' + period
    req = Request(uri, headers={'User-Agent': 'Mozilla/5.0 (research-only)', 'Accept': 'application/json'})
    try:
        with urlopen(req, timeout=10) as response:
            document = json.load(response)
        series = document['chart']['result'][0]
        q = series['indicators']['quote'][0]
        out = pd.DataFrame({
            'time': pd.to_datetime(series['timestamp'], unit='s', utc=True).tz_convert(IST),
            'open': q['open'], 'high': q['high'], 'low': q['low'], 'close': q['close'], 'volume': q['volume'],
        }).dropna(subset=['open', 'high', 'low', 'close'])
        if out.empty:
            raise ValueError('No valid price history returned')
    except (TimeoutError, HTTPError, URLError, OSError, ValueError, TypeError, KeyError, IndexError) as exc:
        raise ValueError('Public research-price provider unavailable or rate-limited') from exc
    CACHE[key] = (now + 300, out.copy())
    return out


@lru_cache(maxsize=1)
def fallback_symbols() -> pd.DataFrame:
    return fallback_equities()

_UNIVERSE_CACHE: tuple[float, pd.DataFrame, str] | None = None


def symbol_directory() -> tuple[pd.DataFrame, str]:
    # Suppress third-party directory fetches as well in the safety default.
    if public_market_data_safety_mode():
        return fallback_symbols(), 'Offline example symbol directory; no quotes'
    global _UNIVERSE_CACHE
    if _UNIVERSE_CACHE and _UNIVERSE_CACHE[0] > time.monotonic():
        return _UNIVERSE_CACHE[1], _UNIVERSE_CACHE[2]
    try:
        req = Request(EQUITY_URL, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'text/csv,*/*'})
        with urlopen(req, timeout=8) as response:
            raw = response.read(8_000_001)
        result = load_equity_csv(raw)
        origin = 'Public NSE reference directory (cached); listing, not live quotes'
    except (HTTPError, URLError, OSError, TimeoutError, ValueError) as exc:
        result, origin = fallback_symbols(), 'Small built-in sample only; NSE reference download unavailable'
    _UNIVERSE_CACHE = (time.monotonic() + (3600 * 12 if len(result) > 100 else 900), result, origin)
    return result, origin


def is_stale(ts: pd.Timestamp, days: int = 10) -> bool:
    instant = pd.Timestamp(ts)
    if instant.tzinfo is None:
        return True
    return datetime.now(IST) - instant.to_pydatetime().astimezone(IST) > timedelta(days=days)


def stock_report(ticker: str, capital: float, risk_pct: float) -> dict:
    """Descriptive historical stock research: no security-specific trade levels."""
    if not (1000 <= capital <= 50_000_000 and .1 <= risk_pct <= 5):
        raise ValueError('Capital must be ₹1,000–₹5 crore; planned risk 0.1–5%.')
    symbol = normalize_ticker(ticker)
    frame = validate_ohlcv(yahoo_history(symbol, '1y'))
    snap = technical_snapshot(frame)
    timestamp = snap['asof']
    stale = is_stale(timestamp)
    caution = []
    if stale:
        caution.append('The last candle is older than 10 days; check the historical timestamp.')
    if snap['rsi14'] > 70:
        caution.append('RSI above 70 indicates elevated historical momentum and possible reversals.')
    if snap['vol_annual_pct'] > 50:
        caution.append('Historical volatility is high and market prices can gap unexpectedly.')
    if snap['price'] <= snap['sma20']:
        caution.append('Price is below its 20-session average; past trend evidence is mixed.')
    if not caution:
        caution = ['Historical prices and patterns cannot predict future market performance.']
    # Virtual budget is user controlled; no entry, stop, target or quantity is generated.
    return {
        'symbol': symbol, 'price': round(float(snap['price']), 2),
        'time': timestamp.isoformat(),
        'data_source': 'Unofficial Yahoo historical daily prices',
        'stale': stale,
        'bias': snap['bias'],
        'indicators': {k: round(float(snap[k]), 2) if snap[k] is not None else None for k in
            ('sma20', 'sma50', 'rsi14', 'atr14', 'momentum20_pct', 'vol_annual_pct')},
        'budget': {
            'capital': round(capital, 2),
            'risk_pct': round(risk_pct, 2),
            'risk_budget': round(capital * risk_pct / 100, 2),
            'allocation_limit': round(capital * .25, 2),
        },
        'observations': snap['observations'],
        'risks': caution,
        'note': 'Historical educational statistics and user-defined virtual risk amount, not a trade plan.',
    }

class RiskRequest(BaseModel):
    capital: float = Field(default=50000, gt=0, le=50000000)
    risk_pct: float = Field(default=1, gt=0, le=5)
    allocation_pct: float = Field(default=25, gt=0, le=100)
    entry: float = Field(gt=0)
    stop: float = Field(gt=0)
    target: float = Field(gt=0)


class DerivativeRequest(BaseModel):
    kind: str
    capital: float = Field(default=50000, gt=0, le=50000000)
    risk_pct: float = Field(default=1, gt=0, le=5)
    allocation_pct: float = Field(default=25, gt=0, le=100)
    premium: float = Field(default=20, ge=0)
    lot_size: int = Field(default=75, ge=1, le=100000)
    strike: float = Field(default=24000, ge=0)
    spot: float = Field(default=24000, ge=0)
    futures_price: float = Field(default=24000, ge=0)
    margin_per_lot: float = Field(default=100000, ge=0)
    stop_points: float = Field(default=100, ge=0)


@app.get('/api/terminal/config')
def terminal_config():
    return {
        'intervals': {key: list(ranges) for key, ranges in CANDLE_RANGES.items()},
        'future_horizons': [5, 10, 20, 40],
        'paper_only': True,
        'market_data_safety_mode': public_market_data_safety_mode(),
        'data_note': 'Historical research data, not exchange-verified streaming.'
    }


@app.get('/api/terminal/universe')
def trader_universe(q: str = Query('', max_length=80),
                    limit: int = Query(60, ge=1, le=100),
                    offset: int = Query(0, ge=0, le=20000)):
    directory, origin = symbol_directory()
    q=q.strip()
    if q:
        matched=directory[
            directory['Symbol'].str.contains(q,case=False,regex=False,na=False)
            | directory['Company'].str.contains(q,case=False,regex=False,na=False)
        ]
    else:
        matched=directory
    records=matched.iloc[offset:offset+limit][['Symbol','Company','Series']].fillna('').to_dict(orient='records')
    return {'items':records,'total':len(matched),'loaded_count':len(directory),
            'offset':offset,'has_more':offset+limit<len(matched),'source':origin}


@app.get('/api/terminal/{ticker}')
def trader_terminal(ticker: str, interval: str = Query('1d'),
                    lookback: str = Query('6mo'), horizon: int = Query(10, ge=1, le=40)):
    # Reject impossible interval/history pairs at the public API boundary.
    # Provider calls may be mocked, cached or replaced; input validation must not rely on them.
    if interval not in CANDLE_RANGES or lookback not in CANDLE_RANGES[interval]:
        raise HTTPException(422, 'This candle interval and history range are not supported together.')
    require_public_market_data()
    try:
        return terminal_report(ticker, interval, lookback, horizon)
    except ValueError as exc:
        problem=str(exc)
        is_bad_input=('symbol' in problem.lower() or 'not supported' in problem.lower()
                      or 'horizon' in problem.lower())
        raise HTTPException(422 if is_bad_input else 503, problem) from exc


@app.get('/api/market-data/status')
def public_price_data_status():
    return market_data_status()


@app.get('/api/health')
def health():
    return {'ok': True, 'mode': 'paper-research', 'real_orders': False, 'asof': datetime.now(IST).isoformat()}


@app.get('/api/universe')
def universe(q: str = Query('', max_length=80), limit: int = Query(30, ge=1, le=100)):
    catalog, origin = symbol_directory()
    q = q.strip()
    if q:
        matched = catalog[catalog['Symbol'].str.contains(q, case=False, regex=False, na=False) |
                          catalog['Company'].str.contains(q, case=False, regex=False, na=False)]
    else:
        matched = catalog
    matches = matched.head(limit)[['Symbol', 'Company', 'Series']].fillna('').to_dict(orient='records')
    return {'items': matches, 'loaded_count': len(catalog), 'match_count': len(matched), 'source': origin}


@app.get('/api/indices')
def indices():
    data = indices_table().fillna('')
    return {'items': data.to_dict(orient='records'), 'note': 'Index names are a directory. Price ticker mappings only for explicitly supported symbols.'}


@app.get('/api/stock/{ticker}/analysis')
def analyze(ticker: str, capital: float = Query(50000, gt=0, le=50000000),
            risk_pct: float = Query(1, gt=0, le=5)):
    require_public_market_data()
    try:
        return stock_report(ticker, capital, risk_pct)
    except ValueError as exc:
        raise HTTPException(422 if 'valid' in str(exc).lower() or 'capital' in str(exc).lower() else 503, str(exc)) from exc


@app.get('/api/stock/{ticker}/history')
def candles(ticker: str, period: str = Query('6mo')):
    require_public_market_data()
    try:
        series = yahoo_history(ticker, period)
        series = series.tail(270)
        values = [{'time': row.time.isoformat(), 'close': round(float(row.close), 2),
                   'volume': float(row.volume) if pd.notna(row.volume) else 0}
                  for row in series.itertuples(index=False)]
        return {'symbol': normalize_ticker(ticker), 'items': values,
                'source': 'Unofficial Yahoo historical data; delays possible'}
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get('/api/news')
def news(topic: str = Query('Indian stock market')):
    if not public_headline_feed_enabled():
        return {
            'items': [], 'official_sources': OFFICIAL_LINKS,
            'feed_paused': True, 'note': NEWS_FEED_PAUSED_NOTICE
        }
    try:
        items = read_public_headlines(topic, max_items=12)
        return {'items': [{'title': x['title'], 'url': x['url'],
                           'published': x['published_utc'].isoformat() if x['published_utc'] else None,
                           'source': x['source'], 'mapping': x['mapping']} for x in items],
                'official_sources': OFFICIAL_LINKS, 'feed_paused': False,
                'note': 'Headline mapping describes possible exposure, not actual price causation.'}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post('/api/risk/plan')
def risk_plan(request: RiskRequest):
    try:
        return position_budget(request.capital, request.risk_pct, request.allocation_pct,
                               request.entry, request.stop, request.target,
                               slippage_pct_per_side=.1)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post('/api/derivatives/plan')
def derivatives(request: DerivativeRequest):
    try:
        if request.kind in ('Call (CE)', 'Put (PE)'):
            result = option_long_budget(request.capital, request.risk_pct, request.allocation_pct,
                 request.premium, request.lot_size, request.strike, request.spot, request.kind)
        elif request.kind == 'Long Future':
            result = future_budget(request.capital, request.risk_pct, request.allocation_pct,
                request.futures_price, request.lot_size, request.margin_per_lot, request.stop_points)
        else:
            raise ValueError('Only long calls, long puts and illustrative long futures are supported')
        return {**result, 'hypothetical': True, 'no_order_execution': True}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get('/api/scanner/status')
def scanner_public_status():
    return public_scanner_status()


@app.get('/api/scanner/demo')
def scanner_synthetic_demo():
    return synthetic_scanner_demonstration()


@app.post('/api/scanner/import')
async def scanner(files: list[UploadFile] = File(...), capital: float = Query(50000, gt=0, le=50000000),
                  risk_pct: float = Query(1, gt=0, le=5)):
    # Defence in depth in addition to pre-body middleware.
    if not public_scanner_upload_enabled():
        raise HTTPException(503, SCANNER_PAUSED_NOTICE)
    if not 1 <= len(files) <= 160:
        raise HTTPException(422, 'Upload 1 to 160 daily CSV/ZIP files')
    decoded = []
    total = 0
    for upload in files:
        name = upload.filename or 'unnamed'
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,140}', name) or not name.lower().endswith(('.csv', '.zip')):
            raise HTTPException(422, 'Only named NSE CSV or ZIP files are supported')
        payload = await upload.read(35 * 1024 * 1024 + 1)
        total += len(payload)
        if total > 50 * 1024 * 1024:
            raise HTTPException(413, 'Combined upload limit: 50 MB')
        decoded.append((name, payload))
    try:
        frame, quality = parse_price_uploads(decoded)
        ranked, summary = scan_market(frame, universe=None, capital=capital, risk_pct=risk_pct,
                                       allocation_pct=25.0, min_turnover=2_000_000)
    except (ValueError, MemoryError, OverflowError) as exc:
        raise HTTPException(422, str(exc)) from exc
    ranked = ranked.replace([math.inf, -math.inf], None).where(pd.notna(ranked), None)
    return {'top': ranked.head(100).to_dict(orient='records'), 'eligible_count': len(ranked),
            'quality': quality, 'summary': summary,
            'disclaimer': 'Only symbols with sufficient uploaded history are scanned. No live data or orders.'}


@app.get('/third-party-licenses')
def third_party_licences():
    return FileResponse(FRONTEND / 'third-party-licenses.html', headers={'Cache-Control': 'no-store'})


@app.get('/terms')
def terms_page():
    return FileResponse(FRONTEND / 'terms.html')


@app.get('/privacy')
def privacy_page():
    return FileResponse(FRONTEND / 'privacy.html', headers={'Cache-Control': 'no-store'})


@app.get('/beta')
def beta_page():
    return FileResponse(FRONTEND / 'beta.html')


@app.get('/terminal')
def terminal_page():
    return FileResponse(FRONTEND / 'terminal.html')


@app.get('/')
def index():
    return FileResponse(FRONTEND / 'index.html')


# Static assets and hash-based routing use the same origin as the API.
app.mount('/', StaticFiles(directory=str(FRONTEND), html=True), name='frontend')
