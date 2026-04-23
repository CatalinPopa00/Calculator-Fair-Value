
import urllib.request
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]

def search_for_val():
    ticker = "UBER"
    # Fetch almost all common modules
    modules = "assetProfile,summaryDetail,defaultKeyStatistics,financialData,earningsTrend,earnings"
    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules={modules}"
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
            if "2.45" in raw:
                print("FOUND 2.45!")
                data = json.loads(raw)
                # Find the path
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
                print("2.45 not found in standard modules.")
    except Exception as e:
        print(f"Error: {e}")

search_for_val()
