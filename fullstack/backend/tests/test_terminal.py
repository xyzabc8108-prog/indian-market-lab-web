"""Offline Trader Terminal tests. No external quotes, broker or order placement."""
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from fullstack.backend import main, terminal_engine as te

IST=ZoneInfo("Asia/Kolkata")
client=TestClient(main.app)

@pytest.fixture(autouse=True)
def mock_licensed_data_for_offline_legacy_fixtures(monkeypatch):
    """Opt in only for mocked test provider; deployed default stays blocked."""
    monkeypatch.setenv("IML_PUBLIC_PRICE_DATA_ENABLED", "true")
    monkeypatch.setenv("IML_MARKET_DATA_LICENSE_APPROVED", "true")


def history(n=140, trend=0.16):
    dt=pd.date_range(end=datetime.now(IST),periods=n,freq="B")
    x=np.arange(n,dtype=float)
    price=100 + trend*x + 1.8*np.sin(x/5.0)
    opening=price-(0.4*np.cos(x/3))
    return pd.DataFrame({
        'time':dt,'open':opening,'high':np.maximum(opening,price)+1,
        'low':np.minimum(opening,price)-1,'close':price,
        'volume':np.repeat(100000.,n)
    })

def test_interval_range_allowlist_and_symbol_validation():
    assert te.normalize_ticker('NSE:RELIANCE')=='RELIANCE.NS'
    assert te.normalize_ticker('TCS.NS')=='TCS.NS'
    for bad in ('', 'TCS/../X', '^NSEI','random ?','https://example.com'):
        with pytest.raises(ValueError):
            te.normalize_ticker(bad)
    assert '1d' in te.CANDLE_RANGES and '1m' in te.CANDLE_RANGES
    with pytest.raises(ValueError):
        te.fetch_candles('TCS','1m','5y')

def test_invalid_and_short_history():
    with pytest.raises(ValueError):
        te.validate_candles(pd.DataFrame())
    with pytest.raises(ValueError):
        te.validate_candles(history(12))
    good=te.validate_candles(history())
    assert len(good)==140 and good['close'].notna().all()

def test_scenarios_are_reproducible_ordered_and_not_zero():
    frame=history()
    a=te.scenario_report(frame,10,'TCS:10')
    b=te.scenario_report(frame,10,'TCS:10')
    assert a==b
    assert a['paths']==2500
    assert a['downside']<=a['middle']<=a['upside']
    assert len(a['bands'])==10
    assert all(row['low']<=row['mid']<=row['high'] for row in a['bands'])
    assert 0<=a['modeled_above_reference_pct']<=100
    assert "NOT calibrated" in a['method']

def test_unsupported_horizon():
    for days in (-1,0,41,50):
        with pytest.raises(ValueError):
            te.scenario_report(history(),days,'TCS')

def test_pattern_catalog_and_detector():
    names=[p[0] for p in te.PATTERN_LIBRARY]
    assert len(names)>=20 and len(names)==len(set(names))
    frame=history()
    found=te.detect_patterns(frame)
    assert all(p['name'] in names and p['confirmed'] is False for p in found)
    assert len(found)<=16

def test_reject_invalid_candles():
    frame=history()
    frame.loc[1,'close']=-15
    out=te.validate_candles(frame)
    assert len(out)==len(frame)-1

def test_terminal_report(monkeypatch):
    monkeypatch.setattr(te,'fetch_candles',lambda *args: history())
    report=te.terminal_report('RELIANCE','1d','6mo',10)
    assert report['symbol']=='RELIANCE.NS'
    assert report['trend'] in ('Bullish','Bearish','Sideways')
    assert report['bars'][0]['time']>0
    assert len(report['bars'])==140
    assert report['scenario']['horizon']==10
    assert not any('order placement' in str(x).lower() for x in report.get('bars',[]))

def test_fullscreen_page_and_api(monkeypatch):
    monkeypatch.setattr(te,'fetch_candles',lambda *args: history())
    assert client.get('/terminal').status_code==200
    assert 'TRADER TERMINAL' in client.get('/terminal').text
    config=client.get('/api/terminal/config')
    assert config.status_code==200 and config.json()['paper_only'] is True
    data=client.get('/api/terminal/TCS',params={'interval':'1d','lookback':'6mo','horizon':5})
    assert data.status_code==200, data.text
    assert data.json()['scenario']['horizon']==5
    invalid=client.get('/api/terminal/TCS',params={'interval':'1m','lookback':'5y'})
    assert invalid.status_code==422

def test_terminal_universe_is_paginated(monkeypatch):
    directory=main.fallback_symbols()
    monkeypatch.setattr(main,'symbol_directory',lambda:(directory,'Offline test data'))
    first=client.get('/api/terminal/universe',params={'limit':5,'offset':0})
    second=client.get('/api/terminal/universe',params={'limit':5,'offset':5})
    assert first.status_code==second.status_code==200
    assert len(first.json()['items'])==5
    assert first.json()['items'][0]['Symbol']!=second.json()['items'][0]['Symbol']
    assert second.json()['loaded_count']==len(directory)

def test_provider_unavailable_no_fake_candles(monkeypatch):
    monkeypatch.setattr(te,'fetch_candles',lambda *args: (_ for _ in ()).throw(ValueError('No data')))
    response=client.get('/api/terminal/RELIANCE',params={'interval':'1d','lookback':'1y'})
    assert response.status_code==503
    assert 'No data' in response.json()['detail']


def test_terminal_rejects_invalid_interval_before_provider_call(monkeypatch):
    # The endpoint must reject unsupported pairs even if the provider is mocked.
    calls = []
    def provider(*args):
        calls.append(args)
        return history()
    monkeypatch.setattr(te, 'fetch_candles', provider)
    for interval, lookback in [('1m', '5y'), ('1d', '1d'), ('bogus', '6mo')]:
        response = client.get('/api/terminal/RELIANCE',
                              params={'interval': interval, 'lookback': lookback})
        assert response.status_code == 422
    assert calls == []


def test_documented_timeframes_match_backend():
    assert te.CANDLE_RANGES == {
        '1m': ('1d','5d'), '5m': ('1d','5d'),
        '15m': ('1wk','1mo'), '1h': ('1wk','1mo'),
        '1d': ('3mo','6mo','1y'), '1wk': ('1y','3y','5y')
    }
    # Human-readable 1-week and 3-year periods use a supported provider envelope.
    for interval, period in [('1m','6mo'),('1d','5y'),('1wk','6mo')]:
        resp=client.get('/api/terminal/TCS',params={'interval':interval,'lookback':period})
        assert resp.status_code == 422
