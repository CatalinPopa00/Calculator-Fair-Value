from api.scraper.yahoo import search_companies
import json

def test_search():
    queries = ['m', 'me', 'met', 'nvo', 'aapl']
    for q in queries:
        print(f"\n--- Testing Query: {q} ---")
        results = search_companies(q)
        print(json.dumps(results, indent=2))
        if not results:
            print(f"WARNING: No results for '{q}'")

if __name__ == "__main__":
    test_search()
