"""Regression tests for automatic stock selection and paper risk planning."""
import unittest
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

from quick_stock_core import stock_options, resolve_stock, analyze_stock_bars


def candles(slope=1, end=None, n=252):
    end = pd.Timestamp(end if end is not None else datetime.now(timezone.utc))
    dates = pd.bdate_range(end=end, periods=n, tz="UTC")
    closes = np.linspace(100, 160, n) if slope > 0 else np.linspace(160, 100, n)
    closes += np.sin(np.arange(n)/5)*1.4
    return pd.DataFrame({
        "time": dates, "open": closes, "high": closes+1.5,
        "low": closes-1.5, "close": closes, "volume": np.full(n, 250000)
    })


class AutoStockTests(unittest.TestCase):
    def setUp(self):
        self.options = stock_options(pd.DataFrame([
            {"Symbol":"RELIANCE","Company":"Reliance Industries"},
            {"Symbol":"TCS","Company":"Tata Consultancy Services"},
        ]))

    def test_dropdown_choice(self):
        self.assertEqual(resolve_stock("RELIANCE — Reliance Industries",self.options)[0],"RELIANCE.NS")

    def test_ticker(self):
        self.assertEqual(resolve_stock("NSE:TCS",self.options)[0],"TCS.NS")

    def test_company(self):
        self.assertEqual(resolve_stock("Tata Consultancy Services",self.options)[0],"TCS.NS")

    def test_unknown_ticker_is_marked(self):
        self.assertFalse(resolve_stock("UNVERIFIED",self.options)[2])

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            resolve_stock("BAD/PATH",self.options)

    def test_no_name_guess(self):
        with self.assertRaises(ValueError):
            resolve_stock("Reliance Industries in India",self.options)

    def test_empty_input(self):
        with self.assertRaises(ValueError):
            resolve_stock("",self.options)

    def test_risk_caps(self):
        analysis = analyze_stock_bars(candles(),simulation_paths=1000)
        self.assertLessEqual(analysis["budget"]["planned_loss"], 500.01)
        self.assertLessEqual(analysis["budget"]["investment"], 12500.01)
        self.assertEqual(analysis["model"]["paths"], 1000)

    def test_stale_data(self):
        old = datetime.now(timezone.utc)-timedelta(days=20)
        self.assertTrue(analyze_stock_bars(candles(end=old), simulation_paths=1000)["status"].startswith("STALE"))

    def test_downtrend_waits(self):
        self.assertIn("WAIT / NO-TRADE", analyze_stock_bars(candles(slope=-1),simulation_paths=1000)["status"])

    def test_invalid_history(self):
        with self.assertRaises(ValueError):
            analyze_stock_bars(candles(n=2),simulation_paths=1000)

    def test_small_account(self):
        self.assertLessEqual(analyze_stock_bars(candles(),capital=1000,simulation_paths=1000)["budget"]["investment"],250.01)

    def test_naive_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            analyze_stock_bars(candles(),as_of=datetime(2026,11,1),simulation_paths=1000)


if __name__ == "__main__":
    unittest.main()
