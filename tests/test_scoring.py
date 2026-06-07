import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.scoring import calculate_rule_of_40

class TestCalculateRuleOf40(unittest.TestCase):
    def test_empty_metrics(self):
        result = calculate_rule_of_40({})
        self.assertEqual(result["revenue_growth"], 0.0)
        self.assertEqual(result["fcf_margin"], 0.0)
        self.assertEqual(result["total"], 0.0)
        self.assertFalse(result["passed"])
        self.assertEqual(result["label"], "Weak")

    def test_forward_revenue_growth_scenario(self):
        metrics = {
            "forward_revenue_growth": 0.25, # 25%
            "historical_anchors": [
                {"year": "2023", "revenue_b": 100, "fcf_b": 20, "ebitda_b": 25}
            ]
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["revenue_growth"], 25.0)
        self.assertEqual(result["fcf_margin"], 20.0) # (20/100) * 100
        self.assertEqual(result["total"], 45.0)
        self.assertTrue(result["passed"])
        self.assertEqual(result["label"], "Strong")
        self.assertEqual(result["rev_growth_label"], "Fwd 1Y Revenue Growth (Scenario)")

    def test_estimate_growth_scenario(self):
        metrics = {
            "rev_estimates": [{"status": "estimate", "growth": 0.15}],
            "historical_anchors": [
                {"year": "2023", "revenue_b": 100, "fcf_b": 20, "ebitda_b": 25}
            ]
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["revenue_growth"], 15.0)
        self.assertEqual(result["fcf_margin"], 20.0)
        self.assertEqual(result["total"], 35.0)
        self.assertFalse(result["passed"])
        self.assertEqual(result["label"], "Healthy")
        self.assertEqual(result["rev_growth_label"], "Fwd 1Y Revenue Growth")

    def test_historical_trends_vs_anchor_growth(self):
        metrics = {
            "historical_trends": [{"year": "2024 (Est)", "revenue": 120000000000}], # 120B
            "historical_anchors": [
                {"year": "2023", "revenue_b": 100, "fcf_b": 10, "ebitda_b": 15}
            ]
        }
        result = calculate_rule_of_40(metrics)
        # fy1_rev_b = 120, fy0_rev = 100. Growth = (120/100) - 1.0 = 0.2 -> 20.0%
        self.assertEqual(result["revenue_growth"], 20.0)
        self.assertEqual(result["fcf_margin"], 10.0)
        self.assertEqual(result["total"], 30.0)
        self.assertFalse(result["passed"])
        self.assertEqual(result["label"], "Weak")

    def test_forward_rev_vs_ttm_rev_growth(self):
        metrics = {
            "company_profile": {
                "forward_revenue": 110,
                "total_revenue": 100
            },
            "historical_anchors": [
                {"year": "2023", "revenue_b": 100, "fcf_b": 5, "ebitda_b": 10}
            ]
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["revenue_growth"], 10.0)
        self.assertEqual(result["fcf_margin"], 5.0)
        self.assertEqual(result["total"], 15.0)
        self.assertFalse(result["passed"])
        self.assertEqual(result["label"], "Weak")

    def test_fallback_revenue_growth(self):
        metrics = {
            "revenue_growth": 0.05,
            "historical_anchors": [
                {"year": "2023", "revenue_b": 100, "fcf_b": 5, "ebitda_b": 10}
            ]
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["revenue_growth"], 5.0)
        self.assertEqual(result["rev_growth_label"], "Revenue Growth")

    def test_margin_waterfall_fcf(self):
        metrics = {
            "revenue_growth": 0.1,
            "historical_anchors": [
                {"year": "2023", "revenue_b": 100, "fcf_b": 15, "ebitda_b": 10}
            ]
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["fcf_margin"], 15.0)
        self.assertEqual(result["margin_label"], "FCF Margin")

    def test_margin_waterfall_ebitda(self):
        metrics = {
            "revenue_growth": 0.1,
            "historical_anchors": [
                {"year": "2023", "revenue_b": 100, "fcf_b": -5, "ebitda_b": 10}
            ]
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["fcf_margin"], 10.0) # Uses EBITDA
        self.assertEqual(result["margin_label"], "EBITDA Margin")

    def test_margin_waterfall_negative_ebitda(self):
        metrics = {
            "revenue_growth": 0.1,
            "historical_anchors": [
                {"year": "2023", "revenue_b": 100, "fcf_b": -5, "ebitda_b": -10}
            ]
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["fcf_margin"], -10.0) # Still uses EBITDA
        self.assertEqual(result["margin_label"], "EBITDA Margin")

    def test_edge_case_fy0_rev_zero(self):
        metrics = {
            "historical_anchors": [
                {"year": "2023", "revenue_b": 0, "fcf_b": 10, "ebitda_b": 20}
            ]
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["fcf_margin"], 0.0) # Avoids division by zero
        self.assertEqual(result["revenue_growth"], 0.0)

    def test_edge_case_bad_types(self):
        metrics = {
            "company_profile": {
                "forward_revenue": "bad",
                "total_revenue": None
            },
            "historical_anchors": [
                {"year": "2023", "revenue_b": "N/A", "fcf_b": {}, "ebitda_b": []}
            ],
            "forward_revenue_growth": "invalid"
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["revenue_growth"], 0.0)
        self.assertEqual(result["fcf_margin"], 0.0)
        self.assertEqual(result["total"], 0.0)

    def test_edge_case_large_rev_growth_not_multiplied(self):
        # The logic: rev_growth = rev_growth_raw * 100.0 if (0 < abs(rev_growth_raw) < 1.0) else rev_growth_raw
        metrics = {
            "forward_revenue_growth": 1.5, # > 1.0, so it shouldn't be multiplied by 100
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["revenue_growth"], 1.5)

        metrics2 = {
            "forward_revenue_growth": -1.5, # abs > 1.0
        }
        result2 = calculate_rule_of_40(metrics2)
        self.assertEqual(result2["revenue_growth"], -1.5)

    def test_edge_case_negative_rev_growth_multiplied(self):
        metrics = {
            "forward_revenue_growth": -0.25, # abs < 1.0, so it should be multiplied by 100
        }
        result = calculate_rule_of_40(metrics)
        self.assertEqual(result["revenue_growth"], -25.0)

if __name__ == '__main__':
    unittest.main()
