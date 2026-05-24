import sys
sys.path.append(r"c:\Users\Snoozie\Downloads\Calculator-Fair-Value")

from models.scoring import calculate_health_score
import json

metrics = {
    "sector": "Industrials",
    "industry": "Aerospace & Defense",
    "beneish_data": {
        "current": {
            "net_receivables": 120,
            "sales": 1000,
            "gross_profit": 400,
            "current_assets": 500,
            "ppe": 800,
            "total_assets": 2000,
            "depreciation": 50,
            "sga": 150,
            "current_liabilities": 300,
            "long_term_debt": 600,
            "cfo": 100,
            "net_income_cont": 200
        },
        "prev": {
            "net_receivables": 100,
            "sales": 900,
            "gross_profit": 350,
            "current_assets": 450,
            "ppe": 850,
            "total_assets": 1900,
            "depreciation": 45,
            "sga": 130,
            "current_liabilities": 250,
            "long_term_debt": 550
        }
    }
}

res = calculate_health_score(metrics)
print("Beneish M-Score Results:")
print(json.dumps(res['beneish'], indent=2))
print("Health Score Total:", res['total'])

print("\n--- Testing Guard Clause (Financials) ---")
metrics_fin = metrics.copy()
metrics_fin["sector"] = "Financials"
res_fin = calculate_health_score(metrics_fin)
print(json.dumps(res_fin['beneish'], indent=2))

print("\n--- Testing High Risk ---")
metrics_bad = metrics.copy()
metrics_bad["beneish_data"]["current"]["net_receivables"] = 400 # Inflated receivables
metrics_bad["beneish_data"]["current"]["net_income_cont"] = 500 # Huge artificial profit
res_bad = calculate_health_score(metrics_bad)
print(json.dumps(res_bad['beneish'], indent=2))
print("Health Score Total after penalty:", res_bad['total'])
