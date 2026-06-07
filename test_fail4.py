import time
import requests
import urllib.parse
import concurrent.futures

def search_conc_fast(query: str):
    search_query = query.strip()
    hosts = ["fake.host.that.times.out.com", "query1.finance.yahoo.com"]
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*"
    }

    def fetch_host(host):
        url = f"https://{host}/v1/finance/search?q={urllib.parse.quote(search_query)}&quotesCount=25&newsCount=0&enableFuzzyQuery=true"
        if "fake" in host:
            time.sleep(2)
            raise requests.exceptions.Timeout("Timeout")
        response = requests.get(url, headers=headers, timeout=2)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            return None
        return None

    # Using concurrent.futures.ThreadPoolExecutor
    # But returning immediately on first success
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(hosts)) as executor:
        # submit all tasks
        futures = {executor.submit(fetch_host, host): host for host in hosts}
        for future in concurrent.futures.as_completed(futures):
            try:
                data = future.result()
                if data:
                    return data
            except Exception as e:
                pass
    return None

start = time.time()
search_conc_fast("AAPL")
print(f"Concurrent with delayed failing host (early return): {time.time() - start:.4f}s")
