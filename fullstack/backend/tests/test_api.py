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
    assert d['budget']['planned_loss'] <= 500
    assert d['plan']['stop'] < d['plan']['entry'] < d['plan']['target']
    assert d['decision'] in ('CONDITIONAL PAPER PLAN','WAIT / NO PAPER TRADE')
    assert client.get('/api/stock/RELIANCE/history').status_code == 200


def test_stale_data_forces_wait(monkeypatch):
    frame=fake_bars()
    frame['time'] = pd.date_range(end=datetime.now(IST)-timedelta(days=90), periods=len(frame), freq='B')
    monkeypatch.setattr(main, 'yahoo_history', lambda *args: frame)
    report=client.get('/api/stock/INFY/analysis').json()
    assert report['stale'] is True
    assert report['decision'] == 'WAIT / NO PAPER TRADE'


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
