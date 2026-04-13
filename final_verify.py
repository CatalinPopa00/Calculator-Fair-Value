from api.scraper.yahoo import get_company_data, get_competitors_data
from api.models.valuation import calculate_reverse_dcf
import json

def verify():
    print("--- Verifying INTU Fix ---")
    data_intu = get_company_data("INTU")
    if data_intu:
        print("Data fetch: SUCCESS")
        # Test the specific crash point
        try:
            res = calculate_reverse_dcf(
                data_intu['current_price'], 
                data_intu['fcf'], 
                0.10, 0.02, 
                data_intu['shares_outstanding'], 
                data_intu.get('total_cash'), 
                data_intu.get('total_debt')
            )
            print(f"Reverse DCF: SUCCESS (Growth: {res})")
        except Exception as e:
            print(f"Reverse DCF: FAILED ({e})")
    else:
        print("Data fetch: FAILED")

    print("\n--- Verifying NVO Competitors ---")
    peers_nvo = get_competitors_data("NVO", "Healthcare", "Drug Manufacturers", 0)
    print(f"NVO Peers: {peers_nvo}")
    if peers_nvo:
        print("Verification: SUCCESS")
    else:
        print("Verification: FAILED")

if __name__ == "__main__":
    verify()
