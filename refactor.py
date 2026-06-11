import re
with open('scraper/yahoo.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Strip fx_rate usage in calculate_historic_pe
text = text.replace('def calculate_historic_pe(stock, financials, fx_rate=1.0):', 'def calculate_historic_pe(stock, financials):')
text = text.replace('pe_ratios.append(price / (eps * fx_rate))', 'pe_ratios.append(price / eps)')
text = text.replace('historic_pe_val = calculate_historic_pe(stock, financials, fx_rate)', 'historic_pe_val = calculate_historic_pe(stock, financials)')

# 2. Strip fx_rate usages
text = text.replace(' * fx_rate', '')
text = text.replace(' * (fx_rate or 1.0)', '')
text = text.replace(', fx_rate=1.0', '')
text = text.replace(' fx_rate=fx_rate,', '')
text = text.replace(' fx_rate=None,', '')
text = text.replace(' fx_rate=fx_rate', '')
text = text.replace(' fx_rate=None', '')
text = text.replace('fx_rate = get_fx_rate(info)', '')
text = text.replace('peer_fx = get_fx_rate(inf)', 'peer_price_usd, peer_fin_usd = get_usd_conversion_rates(inf)')
text = text.replace('if fx_rate is None:\n            fx_rate = get_fx_rate(info)\n', '')

# 3. Replace get_fx_rate with get_usd_conversion_rates
pattern = r'def get_fx_rate\(info: dict\) -> float:.*?return 1\.0\n'
new_func = '''_fx_cache = {}

def get_usd_conversion_rates(info: dict) -> tuple[float, float]:
    """Returns (price_to_usd, fin_to_usd) rates."""
    fin_curr = info.get('financialCurrency', 'USD')
    price_curr = info.get('currency', 'USD')
    
    def get_rate(curr):
        if not curr or curr == 'USD': return 1.0
        if curr in _fx_cache: return _fx_cache[curr]
        try:
            fx_symbol = f"{curr}USD=X"
            fx_ticker = yf.Ticker(fx_symbol)
            fx_hist = fx_ticker.history(period="1d")
            if not fx_hist.empty:
                rate = float(fx_hist['Close'].iloc[-1])
                _fx_cache[curr] = rate
                return rate
        except: pass
        return 1.0
        
    return get_rate(price_curr), get_rate(fin_curr)
'''

text = re.sub(pattern, new_func, text, flags=re.DOTALL)

with open('scraper/yahoo.py', 'w', encoding='utf-8') as f:
    f.write(text)
