import yfinance as yf
import pandas as pd

def check_o_shares():
    o = yf.Ticker("O")
    bs = o.balance_sheet
    if bs is not None and not bs.empty:
        shares_idx = 'Ordinary Shares Number'
        if shares_idx not in bs.index:
            shares_idx = 'Share Issued'
            
        if shares_idx in bs.index:
            shares = bs.loc[shares_idx].dropna()
            print("Shares History:")
            print(shares)
            
            vals = shares.head(4).tolist()
            yoy_rates = []
            for i in range(len(vals) - 1):
                s_new = vals[i]
                s_old = vals[i + 1]
                rate = (s_old - s_new) / s_old
                yoy_rates.append(rate)
                print(f"YoY {i}: {rate*100:.2f}%")
            
            if yoy_rates:
                avg = sum(yoy_rates) / len(yoy_rates)
                print(f"Average: {avg*100:.2f}%")

if __name__ == "__main__":
    check_o_shares()
