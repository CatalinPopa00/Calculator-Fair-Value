
"""
v219 Verification Script - Simulates the exact pipeline for UBER
to verify the Tax Normalization and Source J blocking work correctly.
"""
import yfinance as yf
import pandas as pd
import datetime
import requests

ticker = "UBER"
s = yf.Ticker(ticker)
f = s.income_stmt

print("=" * 60)
print(f"  v219 VERIFICATION FOR {ticker}")
print("=" * 60)

# 1. What does Nasdaq Neutralizer produce?
print("\n--- STEP 1: Nasdaq Neutralizer ---")
try:
    resp = requests.get(
        f"https://api.nasdaq.com/api/company/{ticker}/earnings-surprise",
        headers={"User-Agent": "Mozilla/5.0"}, timeout=10
    ).json()
    rows = resp['data']['earningsSurpriseTable']['rows']
    neutralized_sum = 0
    for row in rows:
        actual = float(row['eps'])
        forecast = float(row['consensusForecast'])
        diff = abs(actual - forecast)
        threshold_pct = diff / abs(forecast) if forecast != 0 else 0
        if threshold_pct > 0.25 or diff > 0.15:
            print(f"  {row['fiscalQtrEnd']}: Actual={actual}, Forecast={forecast} -> NEUTRALIZED to {forecast}")
            neutralized_sum += forecast
        else:
            print(f"  {row['fiscalQtrEnd']}: Actual={actual}, Forecast={forecast} -> KEPT as {actual}")
            neutralized_sum += actual
    print(f"  Neutralized Annual Sum: ${neutralized_sum:.2f}")
except Exception as e:
    print(f"  Nasdaq error: {e}")
    neutralized_sum = None

# 2. What does Source J (SBC Reconstruction) produce?
print("\n--- STEP 2: Source J (SBC Reconstruction) ---")
try:
    q_eh = s.earnings_history
    q_cf = s.quarterly_cashflow
    q_fin = s.quarterly_financials
    if q_eh is not None and not q_eh.empty:
        sorted_q = q_eh.sort_index(ascending=False).head(4)
        sbc_ttm = 0
        for q_date, q_row in sorted_q.iterrows():
            gaap_q = q_row.get('epsActual')
            if gaap_q is not None:
                sbc_ttm += float(gaap_q)
        print(f"  Source J raw GAAP sum (no SBC add-back for simplicity): ${sbc_ttm:.2f}")
        print(f"  vs Neutralized sum: ${neutralized_sum:.2f}" if neutralized_sum else "")
        if neutralized_sum and neutralized_sum < sbc_ttm * 0.75:
            print(f"  -> v219 BLOCKS Source J! ({neutralized_sum:.2f} < {sbc_ttm:.2f} * 0.75 = {sbc_ttm*0.75:.2f})")
        else:
            print(f"  -> Source J would OVERWRITE (not blocked)")
except Exception as e:
    print(f"  Source J error: {e}")

# 3. Tax Normalization
print("\n--- STEP 3: Tax Normalization ---")
if not f.empty:
    col = f.columns[0]
    tax = float(f.loc['Tax Provision', col]) if 'Tax Provision' in f.index else 0
    pretax = float(f.loc['Pretax Income', col]) if 'Pretax Income' in f.index else 0
    shares = float(f.loc['Diluted Average Shares', col]) if 'Diluted Average Shares' in f.index else 0
    net_inc = float(f.loc['Net Income', col]) if 'Net Income' in f.index else 0
    diluted_eps = float(f.loc['Diluted EPS', col]) if 'Diluted EPS' in f.index else 0
    
    print(f"  Pretax Income: ${pretax/1e9:.2f}B")
    print(f"  Tax Provision: ${tax/1e9:.2f}B ({'CREDIT!' if tax < 0 else 'normal'})")
    print(f"  Net Income:    ${net_inc/1e9:.2f}B")
    print(f"  Diluted EPS:   ${diluted_eps:.2f}")
    print(f"  Shares:        {shares/1e9:.2f}B")
    
    if tax < 0 and pretax > 0 and shares > 0:
        norm_ni = pretax * (1 - 0.12)
        norm_eps = norm_ni / shares
        print(f"\n  Tax Credit detected! Normalizing...")
        print(f"  Normalized NI = ${pretax/1e9:.2f}B * (1 - 0.12) = ${norm_ni/1e9:.2f}B")
        print(f"  Normalized EPS = ${norm_eps:.2f}")
        
        # Check if it would trigger
        test_adj = neutralized_sum if neutralized_sum else diluted_eps
        if norm_eps > 0 and norm_eps < test_adj * 0.75:
            print(f"  -> v219 Tax Normalization TRIGGERS! {test_adj:.2f} -> {norm_eps:.2f}")
        else:
            print(f"  -> Tax Normalization would NOT trigger (normalized {norm_eps:.2f} vs adj {test_adj:.2f})")

print("\n" + "=" * 60)
print("  EXPECTED FINAL EPS for UBER 2025:")
if neutralized_sum and tax < 0:
    norm_eps_final = pretax * (1 - 0.12) / shares
    # The lower of neutralized quarterly sum vs tax-normalized
    final = min(neutralized_sum, norm_eps_final)
    print(f"  ${final:.2f} (TARGET: ~$2.45)")
print("=" * 60)
