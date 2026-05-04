import yfinance as yf
import urllib.request
import re
import json

def get_market_averages_test():
    pe_t, pe_f = None, None
    try:
        spy = yf.Ticker("SPY")
        info = spy.info
        pe_t = info.get('trailingPE')
        pe_f = info.get('forwardPE')
        print(f"yfinance: TTM={pe_t}, FWD={pe_f}")
    except Exception as e:
        print(f"yfinance failed: {e}")

    if not pe_t:
        try:
            url = "https://finance.yahoo.com/quote/SPY"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read()
                html = content.decode('utf-8')
                match = re.search(r'PE RATIO \(TTM\).*?value[^>]*>([\d\.]+)', html, re.IGNORECASE | re.DOTALL)
                if match:
                    pe_t = float(match.group(1))
                    print(f"Scrape success: PE={pe_t}")
        except Exception as e:
            print(f"Scrape failed: {e}")

    print(f"Final: TTM={pe_t}, FWD={pe_f}")

if __name__ == "__main__":
    get_market_averages_test()
