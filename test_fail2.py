import time
import requests
import urllib.parse
import concurrent.futures

def search_seq(query: str):
    search_query = query.strip()
    hosts = ["fake.host.that.times.out.com", "query1.finance.yahoo.com"]
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*"
    }
    last_error = None
    for host in hosts:
        try:
            url = f"https://{host}/v1/finance/search?q={urllib.parse.quote(search_query)}&quotesCount=25&newsCount=0&enableFuzzyQuery=true"
            # Simulate a timeout delay
            if "fake" in host:
                time.sleep(2)
                raise requests.exceptions.Timeout("Timeout")
            response = requests.get(url, headers=headers, timeout=2)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            last_error = e
            continue
    return None

def search_conc(query: str):
    search_query = query.strip()
    hosts = ["fake.host.that.times.out.com", "query1.finance.yahoo.com"]
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*"
    }
    last_error = None

    def fetch_host(host):
        url = f"https://{host}/v1/finance/search?q={urllib.parse.quote(search_query)}&quotesCount=25&newsCount=0&enableFuzzyQuery=true"
        if "fake" in host:
            time.sleep(2)
            raise requests.exceptions.Timeout("Timeout")
        response = requests.get(url, headers=headers, timeout=2)
        if response.status_code == 200:
            return response.json()
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(hosts)) as executor:
        future_to_host = {executor.submit(fetch_host, host): host for host in hosts}
        for future in concurrent.futures.as_completed(future_to_host):
            host = future_to_host[future]
            try:
                data = future.result()
                if data:
                    # Cancel other futures if possible, but for simplicity we return early here
                    return data
            except Exception as e:
                last_error = e
    return None

start = time.time()
search_seq("AAPL")
print(f"Sequential with delayed failing host: {time.time() - start:.4f}s")

start = time.time()
search_conc("AAPL")
print(f"Concurrent with delayed failing host: {time.time() - start:.4f}s")
