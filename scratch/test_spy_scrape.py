import urllib.request
import re

def test_spy_scrape():
    url = "https://finance.yahoo.com/quote/SPY"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read()
            if response.info().get('Content-Encoding') == 'gzip':
                import gzip
                content = gzip.decompress(content)
            html = content.decode('utf-8')
            # Save a snippet for inspection
            with open("spy_snippet.html", "w", encoding="utf-8") as f:
                f.write(html[:100000])
            
            # Try to find PE
            # Yahoo often uses data-test="PE_RATIO-value"
            match = re.search(r'PE RATIO \(TTM\).*?value[^>]*>([\d\.]+)', html, re.IGNORECASE | re.DOTALL)
            if match:
                print(f"Match 1: {match.group(1)}")
            else:
                print("Match 1 failed")
                
            # Alternative pattern: search for the specific data-test attribute
            match2 = re.search(r'data-test="PE_RATIO-value"[^>]*>([\d\.]+)', html)
            if match2:
                print(f"Match 2: {match2.group(1)}")
            else:
                print("Match 2 failed")

            # Another one: looking for the text directly in a table cell
            match3 = re.search(r'PE Ratio \(TTM\).*?([\d\.]+)', html, re.IGNORECASE)
            if match3:
                print(f"Match 3: {match3.group(1)}")
            else:
                print("Match 3 failed")

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_spy_scrape()
