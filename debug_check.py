import yfinance as yf

# Check what fields Yahoo actually provides for peers
for ticker in ['UBER', 'NOW', 'CRM', 'SHOP', 'SAP']:
    inf = yf.Ticker(ticker).info
    print(f'=== {ticker} ===')
    fields = [
        'ebitda', 'forwardEbitda', 'netIncomeToCommon',
        'totalDebt', 'totalCash', 'marketCap',
        'sharesOutstanding', 'impliedSharesOutstanding',
        'forwardEps', 'enterpriseToEbitda',
        'currentPrice', 'totalRevenue',
        'priceToSalesTrailing12Months',
        'enterpriseValue'
    ]
    for f in fields:
        print(f'  {f}: {inf.get(f)}')
    print()
