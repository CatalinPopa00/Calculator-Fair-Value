import yfinance as yf
import pandas as pd

def check_meta_earnings_dates():
    ticker = "META"
    stock = yf.Ticker(ticker)
    try:
        ed = stock.get_earnings_dates(limit=24)
        print(f"Earnings Dates for {ticker}:")
        print(ed[['Reported EPS', 'Surprise(%)']].head(12))
        
        print("\nIndex Type:", type(ed.index))
        # Simulation of the mapping logic
        for idx, row in ed.iterrows():
            val = row.get('Reported EPS')
            if pd.isna(val): continue
            import datetime as _dt
            adjusted_date = idx - _dt.timedelta(days=65)
            ey = adjusted_date.year # Since fy_end_month is 12
            print(f"Report Date: {idx}, Adjusted Date: {adjusted_date}, Fiscal Year: {ey}, EPS: {val}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_meta_earnings_dates()
