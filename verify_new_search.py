from api.scraper.yahoo import search_companies
import json

def test_search(query):
    print(f"\nTesting search for: '{query}'")
    results = search_companies(query)
    if not results:
        print("No results found.")
        return
    
    for i, res in enumerate(results):
        print(f"{i+1}. {res['ticker']} - {res['name']} ({res['exchange']})")

if __name__ == "__main__":
    test_search("meta")
    test_search("m")
    test_search("a")
    test_search("nvo")
