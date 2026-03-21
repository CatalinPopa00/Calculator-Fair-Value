import yfinance as yf
s = yf.Ticker('NVO')
print(f"Mean: {s.info.get('recommendationMean')}")
print(f"Key: {s.info.get('recommendationKey')}")
rs = s.recommendations_summary
if rs is not None and not rs.empty:
    print(f"Counts: {rs.iloc[0].to_dict()}")
else:
    print("No counts")
