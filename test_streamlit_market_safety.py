"""Step 21.21.7: offline safety checks, no Streamlit or quote provider needed."""
import ast
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit_market_safety import (
    streamlit_price_data_enabled,
    synthetic_demo_rows,
    virtual_risk_budget,
)

ROOT = Path(__file__).resolve().parent


class StreamlitSafetyContractTests(unittest.TestCase):
    def test_off_by_default_even_when_one_operator_flag_is_true(self):
        variables = ("IML_STREAMLIT_PUBLIC_PRICE_ENABLED",
                     "IML_STREAMLIT_DATA_RIGHTS_APPROVED")
        for left, right, expected in (
            (None, None, False),
            ("true", None, False),
            (None, "true", False),
            ("false", "true", False),
            ("true", "false", False),
            ("true", "true", True),
        ):
            values = {variables[0]: left, variables[1]: right}
            with patch.dict(os.environ, {k:v for k,v in values.items() if v is not None},
                            clear=True):
                self.assertEqual(streamlit_price_data_enabled(), expected)

    def test_synthetic_series_deterministic_and_not_quotes(self):
        a = synthetic_demo_rows(65)
        self.assertEqual(a, synthetic_demo_rows(65))
        self.assertEqual(len(a), 65)
        self.assertEqual(set(a[0]), {"Example step", "Synthetic index"})
        self.assertNotIn("RELIANCE", str(a))
        self.assertNotIn("NSE", str(a))
        self.assertNotIn("symbol", str(a))
        self.assertTrue(all(row["Synthetic index"] > 0 for row in a))
        for n in (0, 1, 261):
            with self.assertRaises(ValueError):
                synthetic_demo_rows(n)

    def test_virtual_risk_only_uses_user_inputs(self):
        result = virtual_risk_budget(50000, 1, 25)
        self.assertEqual(result["virtual_risk_amount"], 500)
        self.assertEqual(result["allocation_cap"], 12500)
        self.assertFalse(any(key in result for key in (
            "symbol", "ticker", "entry", "stop", "target", "shares", "signal")))
        for capital, risk, allocation in (
            (100, 1, 25), (50000, 15, 25), (50000, 1, 0)):
            with self.assertRaises(ValueError):
                virtual_risk_budget(capital, risk, allocation)

    def test_streamlit_entrypoint_has_guard_before_legacy_functions(self):
        source = (ROOT / "web_dashboard.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        stop = next(
            node for node in ast.walk(module)
            if (isinstance(node, ast.Call) and
                isinstance(node.func, ast.Attribute) and
                node.func.attr == "stop" and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == "st")
        )
        history = next(
            node for node in module.body if isinstance(node, ast.FunctionDef)
            and node.name == "history"
        )
        self.assertLess(stop.lineno, history.lineno)
        guard = next(
            node for node in module.body if isinstance(node, ast.If)
            and node.lineno < history.lineno
        )
        self.assertIn("streamlit_price_data_enabled", ast.unparse(guard.test))
        self.assertIn("render_safety_mode", ast.unparse(guard))
        self.assertIn("st.stop()", ast.unparse(guard))
        # Legacy provider wrapper must include its own defence-in-depth check.
        self.assertIn("streamlit_price_data_enabled", ast.unparse(history))

    def test_safe_renderer_does_not_call_external_data_providers(self):
        source = (ROOT / "streamlit_market_safety.py").read_text(encoding="utf-8")
        self.assertNotIn("urlopen(", source)
        self.assertNotIn("requests.get(", source)
        self.assertNotIn("yfinance", source)
        self.assertNotIn("query1.finance.yahoo.com", source)


if __name__ == "__main__":
    unittest.main()
