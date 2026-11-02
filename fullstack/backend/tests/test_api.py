"""Offline contract tests; never call actual providers or execute orders."""
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from fullstack.backend import main

client = TestClient(main.app)
IST = ZoneInfo('Asia/Kolkata')


def fake_bars(n=250, drift=0.004):
    dates = pd.date_range(end=datetime.now(IST), periods=n, freq='B')
    prices = [100 * (1+drift)**i for i in range(n)]
    return pd.DataFrame({'time': dates, 'open': prices,
                         'high': [p*1.01 for p in prices],
                         'low': [p*.99 for p in prices],
                         'close': prices, 'volume': [1_000_000]*n})


def test_backend_serves_frontend_and_health():
    assert client.get('/').status_code == 200
    assert 'INDIAN MARKET LAB' in client.get('/app.js').text
    r = client.get('/api/health')
    assert r.status_code == 200 and r.json()['real_orders'] is False



@pytest.mark.parametrize('path', [
    '/', '/terminal', '/beta', '/privacy', '/terms', '/api/health'
])
def test_public_routes_have_security_headers(path):
    response = client.get(path)
    assert response.status_code == 200
    headers = response.headers
    assert headers['strict-transport-security'] == 'max-age=31536000'
    assert "default-src 'self'" in headers['content-security-policy']
    assert "frame-ancestors 'none'" in headers['content-security-policy']
    assert headers['x-content-type-options'] == 'nosniff'
    assert headers['x-frame-options'] == 'DENY'
    assert headers['referrer-policy'] == 'strict-origin-when-cross-origin'
    assert 'geolocation=()' in headers['permissions-policy']


def test_trader_csp_permits_chart_vendor_but_disallows_inline_scripts():
    policy = client.get('/terminal').headers['content-security-policy']
    assert "script-src 'self' https://unpkg.com" in policy
    assert "'unsafe-inline'" not in policy.split('script-src ')[1].split(';')[0]



def test_mobile_layout_styles_are_served_with_cache_busting():
    home = client.get('/')
    terminal = client.get('/terminal')
    assert home.status_code == 200
    assert terminal.status_code == 200
    assert '/styles.css?v=mobile21-17' in home.text
    assert '/terminal.css?v=mobile21-17' in terminal.text
    research_css = client.get('/styles.css').text
    trader_css = client.get('/terminal.css').text
    assert 'Step 21.17: responsive research dashboard' in research_css
    assert 'grid-template-columns: minmax(0, 1fr);' in research_css
    assert 'scroll-snap-type: x proximity;' in research_css
    assert 'Step 21.17: phone-first terminal' in trader_css
    assert trader_css.rfind('.terminal-mode { display: none; }') > trader_css.rfind('.terminal-mode{display:inline-flex;')
    assert 'max-height: calc(100dvh - 20px);' in trader_css
    assert 'overscroll-behavior-x: contain;' in trader_css


def test_universe_and_index_structure(monkeypatch):
    monkeypatch.setattr(main, 'symbol_directory', lambda: (main.fallback_symbols(), 'offline test'))
    r = client.get('/api/universe', params={'q':'reli', 'limit':10})
    assert r.status_code == 200 and r.json()['items'][0]['Symbol'] == 'RELIANCE'
    assert client.get('/api/indices').status_code == 200


@pytest.mark.parametrize('ticker', ['http://evil.test','../secret','RELIANCE/../../','', 'bad space'])
def test_reject_invalid_symbols(ticker):
    with pytest.raises(ValueError):
        main.normalize_ticker(ticker)


def test_stock_report_includes_stale_and_budget(monkeypatch):
    monkeypatch.setattr(main, 'yahoo_history', lambda *args: fake_bars())
    result = client.get('/api/stock/RELIANCE/analysis')
    assert result.status_code == 200
    d = result.json()
    assert d['symbol'] == 'RELIANCE.NS'
    assert d['budget']['risk_budget'] == 500
    assert d['budget']['allocation_limit'] == 12500
    assert 'plan' not in d
    assert 'decision' not in d
    assert 'shares' not in d['budget']
    assert client.get('/api/stock/RELIANCE/history').status_code == 200


def test_stale_data_forces_wait(monkeypatch):
    frame=fake_bars()
    frame['time'] = pd.date_range(end=datetime.now(IST)-timedelta(days=90), periods=len(frame), freq='B')
    monkeypatch.setattr(main, 'yahoo_history', lambda *args: frame)
    report=client.get('/api/stock/INFY/analysis').json()
    assert report['stale'] is True
    assert 'decision' not in report
    assert 'plan' not in report
    assert any('older than 10 days' in msg for msg in report['risks'])


def test_fallback_quote_provider_not_fabricated(monkeypatch):
    def unavailable(*args):
        raise ValueError('Public research-price provider unavailable')
    monkeypatch.setattr(main, 'yahoo_history', unavailable)
    r=client.get('/api/stock/TCS/analysis')
    assert r.status_code == 503
    assert 'unavailable' in r.json()['detail']


def test_risk_plan_limits():
    response=client.post('/api/risk/plan', json={'entry':1000,'stop':950,'target':1100})
    assert response.status_code == 200
    d=response.json()
    assert d['risk_budget']==500
    assert d['investment'] <= 12500
    assert d['planned_loss'] <= 500
    assert client.post('/api/risk/plan',json={'entry':1000,'stop':1050,'target':1100}).status_code==422


def test_derivatives_no_orders_and_risk_cap():
    r=client.post('/api/derivatives/plan',json={'kind':'Call (CE)','premium':20,'lot_size':75})
    assert r.status_code==200 and r.json()['no_order_execution'] is True
    assert r.json()['lots']==0 # one lot costs 1500, above ₹500 risk budget
    assert client.post('/api/derivatives/plan',json={'kind':'Naked short call'}).status_code==422


def test_scanner_requires_multiple_dates_for_ranking():
    content=b'date,symbol,series,open,high,low,close,volume\n2026-10-30,RELIANCE,EQ,100,110,90,105,100000\n'
    r=client.post('/api/scanner/import',files=[('files',('history.csv',content,'text/csv'))])
    assert r.status_code in (200,422)
    if r.status_code==200:
        assert r.json()['eligible_count']==0


def test_scanner_rejects_unexpected_filename():
    r=client.post('/api/scanner/import',files=[('files',('bad.exe',b'danger','application/octet-stream'))])
    assert r.status_code==422


def test_scanner_imports_actual_60_session_csv():
    dates=pd.date_range(end='2026-10-30',periods=65,freq='B')
    text='date,symbol,series,open,high,low,close,volume\n'+''.join(
        f'{d.date()},RELIANCE,EQ,{100+i},{102+i},{99+i},{101+i},200000\n'
        for i,d in enumerate(dates))
    response=client.post('/api/scanner/import',files=[('files',('history.csv',text.encode(),'text/csv'))])
    assert response.status_code == 200, response.text
    report=response.json()
    assert report['summary']['Risk per idea ₹']==500
    assert report['quality']['Price rows']==65
    assert report['eligible_count'] <= 1
