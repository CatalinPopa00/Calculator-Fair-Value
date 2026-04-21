import yfinance as yf
import datetime
import pandas as pd

ticker = yf.Ticker('AAPL')
divs = ticker.dividends
if divs.empty:
    print("No dividends")
else:
    div_annual = divs.groupby(divs.index.year).sum()
    div_years = sorted(div_annual.index.tolist(), reverse=True)
    
    current_streak = 0
    latest_div_year = div_years[0]
    this_year = datetime.datetime.now().year
    
    print(f"Latest div year: {latest_div_year}")
    print(f"Years: {div_years}")
    
    if latest_div_year >= this_year - 1:
        for i in range(len(div_years) - 1):
            curr_yr = div_years[i]
            prev_yr = div_years[i+1]
            if curr_yr - 1 == prev_yr and div_annual[curr_yr] >= div_annual[prev_yr] * 0.98:
                current_streak += 1
            else:
                print(f"Streak broken between {curr_yr} and {prev_yr}")
                break
                
    streak_result = current_streak + (1 if current_streak > 0 else 0)
    print(f"Final Streak: {streak_result}")
