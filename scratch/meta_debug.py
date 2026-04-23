import yfinance as yf
import json

ticker = "META"
stock = yf.Ticker(ticker)

# Check all available methods/attributes
all_attrs = dir(stock)

data = {
    "all_attrs": all_attrs,
    "info": stock.info
}

# Try common estimate methods
try:
    data["earnings_estimate"] = stock.earnings_estimate.to_json()
except:
    pass

try:
    data["recommendations"] = stock.recommendations.to_json()
except:
    pass

try:
    data["earnings_dates"] = stock.earnings_dates.to_json()
except:
    pass

with open("meta_debug_v2.json", "w") as f:
    json.dump(data, f, indent=4)

print("Meta debug data saved to meta_debug_v2.json")
