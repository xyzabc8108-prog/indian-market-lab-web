import unittest
import numpy as np
import pandas as pd
from research_engine import (normalize_symbol,validate_ohlcv,technical_snapshot,
  planning_levels,position_budget,scenario_simulation,option_long_budget,future_budget)
from news_radar import impact_hypotheses


def data(n=280):
    r=np.random.default_rng(42); prices=120*np.exp(np.cumsum(r.normal(0.0004,0.012,n)))
    old=np.r_[prices[0],prices[:-1]]
    high=np.maximum(prices,old)*1.004;low=np.minimum(prices,old)*0.996
    return pd.DataFrame({'time':pd.date_range('2025-01-01',periods=n,freq='B',tz='Asia/Kolkata'),
                         'open':old,'high':high,'low':low,'close':prices,'volume':r.integers(100,10000,n)})

class ModelTests(unittest.TestCase):
    def test_symbols(self):
        self.assertEqual(normalize_symbol('TCS'),'TCS.NS')
        self.assertEqual(normalize_symbol('HDFC BANK'),'HDFCBANK.NS')
        self.assertEqual(normalize_symbol('NIFTY 50'),'^NSEI')
        with self.assertRaises(ValueError):normalize_symbol('bad/url/path')
    def test_technical(self):
        snap=technical_snapshot(data())
        self.assertGreater(snap['atr14'],0)
        self.assertTrue(0<=snap['rsi14']<=100)
        plan=planning_levels(snap)
        self.assertTrue(plan['stop']<plan['entry']<plan['target'])
    def test_sim_determinism(self):
        df=data(); snap=technical_snapshot(df);p=planning_levels(snap)
        a=scenario_simulation(df,p['entry'],p['stop'],p['target'],10,1000)
        b=scenario_simulation(df,p['entry'],p['stop'],p['target'],10,1000)
        self.assertEqual(a,b)
        self.assertAlmostEqual(a['p_target_first']+a['p_stop_first']+a['p_neither'],1.0)
        self.assertLessEqual(a['p05_pct'],a['median_pct'])
        self.assertLessEqual(a['median_pct'],a['p95_pct'])
    def test_sim_guardrails(self):
        snap=technical_snapshot(data());p=planning_levels(snap)
        with self.assertRaises(ValueError):scenario_simulation(data(),p['entry'],p['stop'],p['target'],paths=200000)
        with self.assertRaises(ValueError):scenario_simulation(data(),p['entry'],p['entry']*1.1,p['target'])
    def test_position_risk(self):
        a=position_budget(50000,1,20,100,95,110,1,0.1)
        self.assertLessEqual(a['planned_loss'],500)
        self.assertLessEqual(a['investment'],10000)
        self.assertGreater(a['shares'],0)
        b=position_budget(1000,0.5,20,2000,1900,2200)
        self.assertEqual(b['shares'],0)
    def test_fno(self):
        x=option_long_budget(50000,1,20,100,65,24000,24000,'Call (CE)',25)
        self.assertEqual(x['lots'],0) # 1 lot premium 6500 > risk budget ₹500
        x=option_long_budget(50000,10,100,50,65,24000,24000,'Put (PE)',25)
        self.assertEqual(x['lots'],1)
        self.assertEqual(x['break_even_expiry'],23950)
        f=future_budget(50000,1,20,25000,65,150000,100)
        self.assertEqual(f['lots'],0)
        with self.assertRaises(ValueError):option_long_budget(1000,1,20,1,65,10,10,'Short CE')
    def test_invalid_data(self):
        with self.assertRaises(ValueError):validate_ohlcv(pd.DataFrame({'close':[1,2]}))
        with self.assertRaises(ValueError):validate_ohlcv(data().head(25))
    def test_news_rules(self):
        r=impact_hypotheses('RBI rate cut boosts bank liquidity')
        self.assertTrue(any(x['theme']=='Banking / credit' for x in r['themes']))
        self.assertIn('Positive wording',r['headline_tone'])
        z=impact_hypotheses('Infosys quarterly earnings')
        self.assertIn('INFY',z['named_stocks'])

if __name__=='__main__':unittest.main()