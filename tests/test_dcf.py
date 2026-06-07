import unittest
from models.valuation import calculate_dcf

class TestCalculateDCF(unittest.TestCase):

    def test_missing_arguments(self):
        # Missing fcf
        self.assertIsNone(calculate_dcf(None, 0.1, 0.1, 0.02, 1000))
        # Missing discount rate
        self.assertIsNone(calculate_dcf(100, 0.1, None, 0.02, 1000))
        # Missing shares
        self.assertIsNone(calculate_dcf(100, 0.1, 0.1, 0.02, None))
        self.assertIsNone(calculate_dcf(100, 0.1, 0.1, 0.02, 0))

    def test_happy_path(self):
        result = calculate_dcf(
            fcf=100.0,
            growth_rate=0.10,
            discount_rate=0.09,
            perpetual_growth=0.02,
            shares_outstanding=1000,
            total_cash=50.0,
            total_debt=20.0,
            years=5,
            exit_multiple=15.0
        )
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["discount_rate_applied"], 0.09)
        self.assertEqual(len(result["fcf_years"]), 5)
        self.assertEqual(len(result["pv_fcf_years"]), 5)
        # Year 1 FCF = 100 * 1.1 = 110
        self.assertAlmostEqual(result["fcf_years"][0], 110.0)
        # Year 2 FCF = 110 * 1.1 = 121
        self.assertAlmostEqual(result["fcf_years"][1], 121.0)

        self.assertEqual(result["effective_shares"], 1000)
        self.assertIn("dcf_perpetual", result)
        self.assertIn("dcf_exit_multiple", result)

    def test_negative_fcf(self):
        # Test negative FCF trending to profitability.
        result = calculate_dcf(
            fcf=-100.0,
            growth_rate=0.10,
            discount_rate=0.09,
            perpetual_growth=0.02,
            shares_outstanding=1000
        )
        # First year: -100 + abs(-100)*0.1 = -90
        # Second year: -90 + abs(-90)*0.1 = -81
        self.assertAlmostEqual(result["fcf_years"][0], -90.0)
        self.assertAlmostEqual(result["fcf_years"][1], -81.0)
        self.assertAlmostEqual(result["fcf_years"][4], -59.049)

    def test_list_growth_rate(self):
        result = calculate_dcf(
            fcf=100.0,
            growth_rate=[0.1, 0.2, 0.15],
            discount_rate=0.09,
            perpetual_growth=0.02,
            shares_outstanding=1000,
            years=5
        )
        # Year 1: 100 * 1.1 = 110
        self.assertAlmostEqual(result["fcf_years"][0], 110.0)
        # Year 2: 110 * 1.2 = 132
        self.assertAlmostEqual(result["fcf_years"][1], 132.0)
        # Year 3: 132 * 1.15 = 151.8
        self.assertAlmostEqual(result["fcf_years"][2], 151.8)
        # Year 4: fallback to last element (0.15) -> 151.8 * 1.15 = 174.57
        self.assertAlmostEqual(result["fcf_years"][3], 174.57)
        # Year 5: 174.57 * 1.15 = 200.7555
        self.assertAlmostEqual(result["fcf_years"][4], 200.7555)

    def test_wacc_smart_cap(self):
        # WACC should be capped between 7% and 10.5%
        res_low = calculate_dcf(100.0, 0.1, 0.05, 0.02, 1000)
        self.assertEqual(res_low["discount_rate_applied"], 0.07)

        res_high = calculate_dcf(100.0, 0.1, 0.15, 0.02, 1000)
        self.assertEqual(res_high["discount_rate_applied"], 0.105)

    def test_buybacks_method_a(self):
        # With current price provided
        result = calculate_dcf(
            fcf=100.0,
            growth_rate=0.1,
            discount_rate=0.09,
            perpetual_growth=0.02,
            shares_outstanding=1000,
            buyback_rate=0.05, # 5% per year
            current_price=10.0,
            years=5
        )

        # We expect buyback_cost_per_year to be populated
        self.assertEqual(len(result["buyback_cost_per_year"]), 5)
        # Effective shares should decrease over 5 years
        # Year 1: starts with 1000, buys 50
        # remaining shares drops
        self.assertTrue(result["effective_shares"] < 1000)
        # Ensure cash flow deduction occurred (it should be less than 110)
        self.assertTrue(result["fcf_years"][0] < 110.0)

    def test_buybacks_fallback(self):
        # With current price missing, fallback logic
        result = calculate_dcf(
            fcf=100.0,
            growth_rate=0.1,
            discount_rate=0.09,
            perpetual_growth=0.02,
            shares_outstanding=1000,
            buyback_rate=0.05,
            current_price=None, # triggers fallback
            years=5
        )
        # FCF should be unaffected
        self.assertAlmostEqual(result["fcf_years"][0], 110.0)
        self.assertAlmostEqual(result["fcf_years"][1], 121.0)

        # Buyback costs should be 0
        self.assertEqual(result["buyback_cost_per_year"], [0, 0, 0, 0, 0])
        # Effective shares should still drop: 1000 * 0.95^5
        expected_shares = 1000 * (0.95 ** 5)
        self.assertAlmostEqual(result["effective_shares"], expected_shares)

    def test_terminal_denominator_zero(self):
        # Capping perpetual growth denom if WACC == perpetual growth
        result = calculate_dcf(
            fcf=100.0,
            growth_rate=0.1,
            discount_rate=0.07,  # Caps to 0.07
            perpetual_growth=0.07, # same as discount rate
            shares_outstanding=1000
        )
        # Denominator should be forced to 0.0001
        self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()
