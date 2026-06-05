import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

class DummyResponse:
    def __init__(self):
        self.headers = {}

def main():
    from api.index import get_valuation
    val_data = get_valuation("MA", DummyResponse())
    
    print(f"FCF: {val_data.get('formula_data', {}).get('dcf', {}).get('fcf')}")
    print(f"archetype_weights: {val_data.get('archetype_weights')}")
    if val_data.get('formula_data') and val_data['formula_data'].get('dcf'):
        print(f"Intrinsic Value: {val_data['formula_data']['dcf'].get('intrinsic_value')}")
    else:
        print("DCF missing in formula_data")

if __name__ == "__main__":
    main()
