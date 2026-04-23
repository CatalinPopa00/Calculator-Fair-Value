import requests
import re
import json

def debug_yahoo_analysis(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}/analysis"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {response.status_code}")
    
    html = response.text
    
    # Try to find the JSON blob. Yahoo often uses "root.App.main" or similar.
    # In newer versions, it might be in a script with id="main-content" or similar.
    
    # Look for earningsTrend in the HTML
    trends = re.findall(r'\{"period":"[+-]?\d[yYqQ]".*?\}', html)
    print(f"Found {len(trends)} trend-like segments.")
    
    # Save a chunk of HTML for manual inspection if needed
    with open("yahoo_analysis_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
        
    # Search for the "Avg. Estimate" and "Year Ago EPS" labels in the text
    # to see if they are in a table or just in JSON.
    
    if "Avg. Estimate" in html:
        print("Found 'Avg. Estimate' in HTML text.")
    
    # Look for the specific values the browser subagent found (29.68, 30.12, 35.62)
    for val in ["29.68", "30.12", "35.62"]:
        if val in html:
            print(f"Found value {val} in HTML!")
        else:
            print(f"Value {val} NOT found in raw HTML.")

if __name__ == "__main__":
    debug_yahoo_analysis("META")
