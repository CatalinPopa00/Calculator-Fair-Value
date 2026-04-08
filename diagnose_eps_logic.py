import yfinance as yf
import pandas as pd
import datetime

def diagnostic_eps_mapping(ticker):
    stock = yf.Ticker(ticker)
    fy_end_month = 12 # META
    if ticker == "FDS": fy_end_month = 8
    
    try:
        ed = stock.get_earnings_dates(limit=24)
        if ed is None or ed.empty:
            print(f"No earnings dates for {ticker}")
            return

        adjusted_history = {}
        print(f"--- Raw Earnings Dates for {ticker} ---")
        for idx, row in ed.iterrows():
            val = row.get('Reported EPS')
            if pd.isna(val): continue
            
            # THE LOGIC FROM YAHOO.PY
            adjusted_date = idx - datetime.timedelta(days=65)
            ey = adjusted_date.year if adjusted_date.month <= fy_end_month else adjusted_date.year + 1
            
            key = str(ey)
            if key not in adjusted_history: adjusted_history[key] = []
            adjusted_history[key].append(float(val))
            print(f"Date: {idx.date()}, AdjDate: {adjusted_date.date()}, FY: {ey}, EPS: {val}")

        print(f"\n--- Aggregated Quarters for {ticker} ---")
        for ey, qrs in adjusted_history.items():
            print(f"Year {ey}: {qrs} (Count: {len(qrs)})")

        # SCALING LOGIC
        final_adj_history = {}
        curr_y = 2026 # Simulating current year as per artifact timestamp
        for ey, quarters in adjusted_history.items():
            ey_int = int(ey)
            if len(quarters) >= 3:
                final_adj_history[ey] = sum(quarters) * (4.0 / len(quarters))
            elif len(quarters) >= 1 and ey_int >= (curr_y - 1):
                final_adj_history[ey] = sum(quarters) * (4.0 / len(quarters))
            else:
                final_adj_history[ey] = sum(quarters) # No scale

        print(f"\n--- Final Scaled Non-GAAP History for {ticker} ---")
        for ey, val in sorted(final_adj_history.items()):
            print(f"{ey}: {val:.2f}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("MAPPING FOR META:")
    diagnostic_eps_mapping("META")
    print("\nMAPPING FOR FDS:")
    diagnostic_eps_mapping("FDS")
