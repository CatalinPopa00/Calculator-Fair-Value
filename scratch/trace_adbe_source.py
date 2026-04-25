import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.yahoo import get_nasdaq_actual_eps, get_yahoo_analysis_normalized

ticker = "ADBE"
print(f"Investigating source for {ticker}...")

# 1. Yahoo Analysis
yahoo_data = get_yahoo_analysis_normalized(ticker)
print(f"Yahoo Year Ago: {yahoo_data.get('eps', {}).get('0y', {}).get('yearAgo')}")

# 2. Nasdaq Actual
nasdaq_data = get_nasdaq_actual_eps(ticker)
print(f"Nasdaq Actual (Scraped): {nasdaq_data}")
