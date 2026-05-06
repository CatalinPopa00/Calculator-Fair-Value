import requests
import re
import json

def parse_n(val):
    if not val: return 0.0
    val = str(val).replace('$', '').replace(',', '').strip()
    mult = 1.0
    if 'B' in val: mult = 1e9; val = val.replace('B', '')
    elif 'M' in val: mult = 1e6; val = val.replace('M', '')
    try: return float(val) * mult
    except: return 0.0

def debug_mu(ticker='MU'):
    url = f'https://finance.yahoo.com/quote/{ticker}/analysis'
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}
    resp = requests.get(url, headers=headers)
    html = resp.text
    
    res = {'eps': {}, 'rev': {}}
    
    # Pass 1: HTML Tables
    tables = re.findall(r'<table.*?</table>', html, re.DOTALL)
    for i, table in enumerate(tables):
        first_row = re.search(r'<tr.*?</tr>', table, re.DOTALL)
        if first_row:
            h_clean = re.sub(r'<[^>]+>', ' ', first_row.group(0)).strip()
            print(f"DEBUG: Table {i} Header: {h_clean[:100]}")
        rows = re.findall(r'<tr.*?</tr>', table, re.DOTALL)
        for row in rows:
            clean = re.sub(r'<[^>]+>', ' ', row).strip()
            if 'Avg. Estimate' in clean:
                print(f"DEBUG: Found Row: {clean}")
                m0 = re.search(r'data-testid-cell="0y".*?>\s*([^<]+)', row)
                m1 = re.search(r'data-testid-cell="\+1y".*?>\s*([^<]+)', row)
                v0 = m0.group(1).strip() if m0 else None
                v1 = m1.group(1).strip() if m1 else None
                is_rev = (v0 and ('B' in v0 or 'M' in v0)) or (v1 and ('B' in v1 or 'M' in v1))
                if is_rev:
                    if v0: res['rev']['0y'] = {'avg': parse_n(v0)}
                    if v1: res['rev']['+1y'] = {'avg': parse_n(v1)}
                else:
                    if v0: res['eps']['0y'] = {'avg': parse_n(v0)}
                    if v1: res['eps']['+1y'] = {'avg': parse_n(v1)}

    # Pass 2: JSON Trends
    for trend_key in ["revenueTrend", "earningsTrend", "earningsTrendNonGaap"]:
        parts = html.split(f'"{trend_key}"')
        if len(parts) < 2: parts = html.split(f'\\"{trend_key}\\"')
        if len(parts) < 2: continue
        
        chunk = parts[1][:150000]
        is_nongaap = (trend_key == "earningsTrendNonGaap")
        is_rev_trend = (trend_key == "revenueTrend")
        
        for p in ['0y', '+1y']:
            p_target = f'"{p}"'
            if p_target not in chunk: p_target = f'\\"{p}\\"'
            if p_target not in chunk: continue 
            
            p_idx = chunk.find(p_target)
            sub_chunk = chunk[p_idx:p_idx+2000] 
            
            if not is_rev_trend:
                eps_avg_m = re.search(r'earningsEstimate(?:\"|\\"):\{[^{}]*?avg(?:\"|\\"):\{[^{}]*?raw(?:\"|\\"):([\d\.\-]+)', sub_chunk)
                eps_ya_m = re.search(r'yearAgoEps(?:\"|\\"):\{[^{}]*?raw(?:\"|\\"):([\d\.\-]+)', sub_chunk)
                
                if p not in res['eps']: res['eps'][p] = {}
                if eps_avg_m:
                    val = float(eps_avg_m.group(1))
                    res['eps'][p]['avg'] = val
                    print(f"JSON {trend_key} {p}: EPS Avg {val}")
                if eps_ya_m:
                    val = float(eps_ya_m.group(1))
                    res['eps'][p]['yearAgo'] = val
                    print(f"JSON {trend_key} {p}: EPS YearAgo {val}")
            else:
                rev_avg_m = re.search(r'revenueEstimate(?:\"|\\"):\{[^{}]*?avg(?:\"|\\"):\{[^{}]*?raw(?:\"|\\"):([\d\.\-]+)', sub_chunk)
                if rev_avg_m:
                    val = float(rev_avg_m.group(1))
                    if p not in res['rev']: res['rev'][p] = {}
                    res['rev'][p]['avg'] = val
                    print(f"JSON {trend_key} {p}: Rev Avg {val}")

    print("\nFINAL RESULT:")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else 'MU'
    debug_mu(ticker)
