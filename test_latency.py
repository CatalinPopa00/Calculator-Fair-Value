import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.scraper.yahoo import get_company_data, get_analyst_data, get_competitors_data

ticker = "SMCI"

t0 = time.time()
print("Fetching company data...")
d1 = get_company_data(ticker)
t1 = time.time()
print(f"  Company data took: {t1 - t0:.2f}s")

t0 = time.time()
print("Fetching analyst data...")
d2 = get_analyst_data(ticker)
t1 = time.time()
print(f"  Analyst data took: {t1 - t0:.2f}s")

t0 = time.time()
print("Fetching competitors data...")
d3 = get_competitors_data(ticker)
t1 = time.time()
print(f"  Competitors data took: {t1 - t0:.2f}s")
