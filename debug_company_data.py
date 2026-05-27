import yfinance as yf
from scraper.yahoo import get_company_data

# Simulate what api/index.py receives from get_company_data
data = get_company_data('NOW')
print("=== Fields from get_company_data for NOW ===")
for k in ['market_cap', 'total_debt', 'total_cash', 'ebitda', 
           'forward_ebitda', 'net_income', 'forward_eps', 
           'shares_outstanding', 'current_price', 'revenue',
           'forward_revenue', 'fwd_pe', 'fwd_ps']:
    print(f"  {k}: {data.get(k)}")
