import yfinance as yf
import pandas as pd

def get_yahoo_eps_trend(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        et = stock.earnings_trend
        if et is not None and not et.empty:
            res = {}
            for period_idx, row in et.iterrows():
                p_key = str(period_idx)
                res[p_key] = {
                    'avg': row.get('avg') or row.get('Avg'),
                    'yearAgoEps': row.get('yearAgoEps') or row.get('Year Ago EPS'),
                    'growth': row.get('growth') or row.get('Growth')
                }
            return res
    except: pass
    return {}

ticker = 'AAPL'
trend = get_yahoo_eps_trend(ticker)
print(f"Trend for {ticker}: {trend}")
