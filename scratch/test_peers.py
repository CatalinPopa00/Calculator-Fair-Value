import yfinance as yf

# ADBE's industry is 'Software - Application'
# Let's see what industry the current recommended peers are in
for t in ['CRM', 'PLTR', 'APP', 'NOW', 'INTU', 'MSFT', 'ORCL']:
    try:
        info = yf.Ticker(t).info
        ind = info.get("industry", "?")
        sec = info.get("sector", "?")
        print(f"{t}: {ind} | {sec}")
    except Exception as e:
        print(f"{t}: ERROR - {e}")
