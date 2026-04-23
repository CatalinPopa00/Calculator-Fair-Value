"""v219 Final Verification — EPS Growth Average"""
import yfinance as yf

ticker = "UBER"
s = yf.Ticker(ticker)

# Check what the FY projections produce for growth
# FY0 ($3.37) vs anchor ($2.52): growth = 33.7%  
# FY1 ($4.34) vs FY0 ($3.37): growth = 28.7%
# Average: (33.7 + 28.7) / 2 = 31.2%

fy0_eps = 3.37
anchor_eps = 2.52  # Normalized from v219
fy1_eps = 4.34

g0 = fy0_eps / anchor_eps - 1
g1 = fy1_eps / fy0_eps - 1
avg = (g0 + g1) / 2

print(f"FY0 Growth (from anchor {anchor_eps}): {g0*100:.1f}%")
print(f"FY1 Growth (from FY0 {fy0_eps}): {g1*100:.1f}%")  
print(f"Average Growth: {avg*100:.1f}%")
print()
print(f"Expected EPS Growth (Est.) in sidebar: {avg*100:.1f}%")
print(f"This replaces the GAAP-based 33.75% or -28.7%")
