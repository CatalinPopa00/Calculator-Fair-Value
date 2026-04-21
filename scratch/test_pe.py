import yfinance as yf
import pandas as pd
import datetime

def find_idx(df, pattern):
    for idx in df.index:
        if pattern.lower() in str(idx).lower():
            return idx
    return None

def calculate_historic_pe(stock, financials, fx_rate=1.0):
    if financials is None or financials.empty:
        return None
    try:
        eps_row = None
        if 'Diluted EPS' in financials.index:
            eps_row = financials.loc['Diluted EPS']
        elif 'Basic EPS' in financials.index:
            eps_row = financials.loc['Basic EPS']
        if eps_row is None:
            return None
        eps_values = eps_row.dropna().head(5)
        if eps_values.empty:
            return None
        hist_5y = stock.history(period="5y")
        if hist_5y.empty:
            return None
        if hasattr(hist_5y.index, 'tz_localize') and hist_5y.index.tz is not None:
            hist_5y.index = hist_5y.index.tz_localize(None)
        pe_ratios = []
        for date, eps in eps_values.items():
            if eps <= 0: continue
            try:
                target_date = date.tz_localize(None) if hasattr(date, 'tz_localize') and date.tz is not None else date
                window = hist_5y[(hist_5y.index >= target_date - pd.Timedelta(days=10)) & 
                                 (hist_5y.index <= target_date + pd.Timedelta(days=10))]
                if not window.empty:
                    valid_dates = window[window.index <= target_date]
                    price = float(valid_dates['Close'].iloc[-1]) if not valid_dates.empty else float(window['Close'].iloc[0])
                    pe_ratios.append(price / (eps * fx_rate))
            except: continue
        if not pe_ratios: return None
        return sum(pe_ratios) / len(pe_ratios)
    except Exception as e:
        print(f"Error: {e}")
        return None

ticker = 'ELV'
stock = yf.Ticker(ticker)
financials = stock.financials
print(f"Historic PE for {ticker}: {calculate_historic_pe(stock, financials)}")
