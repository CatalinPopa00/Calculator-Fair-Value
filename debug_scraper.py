from api.scraper.yahoo import get_company_data
import json

def debug_scraper(ticker):
    print(f"Scraping {ticker}...")
    data = get_company_data(ticker)
    if data:
        print("Scrape successful.")
        synthesis = data.get("company_overview_synthesis")
        print(f"Synthesis for {ticker}:")
        print(synthesis)
    else:
        print("Scrape failed.")

if __name__ == "__main__":
    debug_scraper("AAPL")
