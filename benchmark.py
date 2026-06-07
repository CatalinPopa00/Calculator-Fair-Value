import time
from scraper.yahoo import search_companies

def test_search():
    start = time.time()
    for _ in range(5):
        res = search_companies("MSFT")
    end = time.time()
    print(f"Total time for 5 requests: {end - start:.4f}s")

if __name__ == "__main__":
    test_search()
