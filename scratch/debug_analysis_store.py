import requests
import re
import json

def extract_yahoo_analysis_data(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=15)
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None
    
    html = response.text
    
    # Extract the root.App.main JSON
    # Look for root.App.main = { ... };
    match = re.search(r'root\.App\.main\s*=\s*(\{.*?\});', html)
    if not match:
        print("Could not find root.App.main JSON.")
        # Sometimes it's window.App.main
        match = re.search(r'window\.App\.main\s*=\s*(\{.*?\});', html)
        if not match:
             # Try a more aggressive search for the JSON blob in any script tag
             match = re.search(r'\{"context":\{"dispatcher":\{"stores":\{"AnalysisStore":.*?\}\}\}', html)
             if not match:
                 return None

    json_str = match.group(1)
    try:
        data = json.loads(json_str)
        
        # Navigate to AnalysisStore
        # Path: data['context']['dispatcher']['stores']['AnalysisStore']
        stores = data.get('context', {}).get('dispatcher', {}).get('stores', {})
        analysis_store = stores.get('AnalysisStore', {})
        
        # The store might have 'earningsEstimate' and 'trend'
        # We need to find the 'Normalized' vs 'GAAP' toggle or data
        # Usually, Yahoo pre-loads both.
        
        # Let's inspect the keys of analysis_store
        print(f"AnalysisStore keys: {list(analysis_store.keys())}")
        
        # The user wants "Normalized"
        # Often there's an 'isNonGAAP' or similar flag, or just multiple entries.
        
        # Look for trends
        trends = analysis_store.get('trend', [])
        print(f"Found {len(trends)} trends.")
        
        # For each trend, check if it's GAAP or Normalized
        for t in trends:
            period = t.get('period')
            # Check for non-GAAP indicators
            # In some versions, Normalized data is in a separate list or has a flag.
            avg = t.get('earningsEstimate', {}).get('avg', {}).get('raw')
            yearAgo = t.get('earningsEstimate', {}).get('yearAgoEps', {}).get('raw')
            print(f"Period: {period}, Avg: {avg}, YearAgo: {yearAgo}")

        return analysis_store
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return None

if __name__ == "__main__":
    extract_yahoo_analysis_data("META")
