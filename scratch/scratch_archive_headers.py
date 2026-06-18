import requests
url = "https://archive.is/newest/https://www.wsj.com/"
try:
    response = requests.head(url, allow_redirects=True)
    print("Headers:")
    for k, v in response.headers.items():
        if "frame" in k.lower() or "csp" in k.lower() or "sec" in k.lower():
            print(f"{k}: {v}")
    print("All headers:", response.headers)
except Exception as e:
    print(e)
