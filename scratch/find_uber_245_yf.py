
import yfinance as yf
import json

def search_yf():
    ticker = "UBER"
    s = yf.Ticker(ticker)
    modules = "assetProfile,summaryDetail,defaultKeyStatistics,financialData,earningsTrend,earnings"
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules={modules}"
    
    resp = s.session.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    raw = resp.text
    if "2.45" in raw:
        print("FOUND 2.45!")
        data = resp.json()
        def find_path(d, target, path=""):
            if isinstance(d, dict):
                for k, v in d.items():
                    find_path(v, target, path + "." + k)
            elif isinstance(d, list):
                for i, v in enumerate(d):
                    find_path(v, target, path + f"[{i}]")
            else:
                if str(d) == str(target):
                    print(f"Path: {path} = {d}")
        find_path(data, "2.45")
    else:
        print("2.45 not found in response.")
        # Print a bit of the JSON to see what we DID get
        # print(raw[:1000])

search_yf()
