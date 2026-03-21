from api.scraper.yahoo import get_company_data

def verify_historic_pe(ticker):
    print(f"Fetching data for {ticker}...")
    data = get_company_data(ticker)
    if not data:
        print("Failed to fetch data.")
        return
    
    pe_historic = data.get("pe_historic")
    trailing_pe = data.get("pe_ratio")
    
    print(f"Ticker: {ticker}")
    print(f"Trailing P/E: {trailing_pe}")
    print(f"Historic P/E (5-yr avg): {pe_historic}")
    
    if pe_historic and trailing_pe:
        diff = abs(pe_historic - trailing_pe)
        print(f"Difference: {diff:.2f}")
        if diff < 0.01:
            print("WARNING: Historic PE is almost identical to Trailing PE. Check if calculation is working or if they are just close.")
        else:
            print("Historic PE differs from Trailing PE as expected.")
    else:
        print("Missing PE data.")

if __name__ == "__main__":
    verify_historic_pe("AAPL")
    verify_historic_pe("META")
