"""Quick diagnostic: what does yfinance actually report for TSM?"""
import yfinance as yf

stock = yf.Ticker("TSM")
info = stock.info

print("=== INFO TAGS (should be USD for ADR) ===")
print(f"  trailingEps:     {info.get('trailingEps')}")
print(f"  forwardEps:      {info.get('forwardEps')}")
print(f"  trailingPE:      {info.get('trailingPE')}")
print(f"  forwardPE:       {info.get('forwardPE')}")
print(f"  currency:        {info.get('currency')}")
print(f"  financialCurrency: {info.get('financialCurrency')}")
print(f"  sharesOutstanding: {info.get('sharesOutstanding')}")
print(f"  impliedSharesOutstanding: {info.get('impliedSharesOutstanding')}")

print("\n=== FINANCIALS (raw - what currency?) ===")
fin = stock.financials
if fin is not None and not fin.empty:
    for label in ['Net Income', 'Net Income Common Stock Holders', 'Total Revenue', 'Diluted EPS', 'Basic EPS']:
        try:
            row = fin.loc[label] if label in fin.index else None
            if row is not None:
                print(f"  {label}: {float(row.iloc[0]):,.2f} | {float(row.iloc[1]):,.2f}")
        except:
            pass

print("\n=== QUARTERLY FINANCIALS ===")
qfin = stock.quarterly_financials
if qfin is not None and not qfin.empty:
    for label in ['Net Income', 'Diluted EPS', 'Basic EPS']:
        try:
            row = qfin.loc[label] if label in qfin.index else None
            if row is not None:
                vals = [f"{float(v):,.4f}" for v in row.iloc[:4]]
                print(f"  {label}: {vals}")
        except:
            pass
