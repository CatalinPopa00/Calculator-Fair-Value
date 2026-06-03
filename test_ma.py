import sys
sys.path.insert(0, r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\Calculator-Fair-Value')
from scraper.yahoo import get_company_data
from models.scoring import calculate_health_score, calculate_buy_score, clean_percent, clean_ratio

for ticker in ['V', 'MA']:
    print(f'\n{"="*60}')
    print(f'=== {ticker} ===')
    print(f'{"="*60}')
    data = get_company_data(ticker)
    
    if data.get('error'):
        print(f'ERROR: {data["error"]}')
        continue

    pe_historic = data.get("pe_historic") or data.get("pe_ratio")
    
    valuation_data = {
        "margin_of_safety": 0,
        "sector_median_peg": 0,
        "sector_median_pe": 0,
        "sector_median_ps": 0,
        "sector_median_ev_ebitda": 0,
        "sector_median_pb": 0,
        "historic_pe": pe_historic if pe_historic else 0,
        "market_cap": data.get("shares_outstanding", 0) * data.get("current_price", 0) if data.get("shares_outstanding") and data.get("current_price") else 0.0
    }

    h_result = calculate_health_score(data)
    roic_val = clean_percent(data.get('roic'))
    fwd_pe = clean_ratio(data.get('forward_pe') or data.get('fwd_pe'))
    hist_pe = clean_ratio(pe_historic)
    
    is_monopoly = (roic_val > 20.0 and h_result['total'] >= 70.0)
    
    print(f'ROIC: {roic_val:.1f}% | Health: {h_result["total"]} | Monopoly: {is_monopoly}')
    print(f'Fwd PE: {fwd_pe:.2f} | Hist PE: {hist_pe:.2f}')
    
    if fwd_pe > 0 and hist_pe > 0:
        discount = ((hist_pe - fwd_pe) / hist_pe) * 100.0
        print(f'Discount: {discount:.2f}%')
    
    b_result = calculate_buy_score(valuation_data, data)
    for item in b_result['breakdown']:
        if 'P/E' in item['metric']:
            print(f'  -> {item["metric"]}: {item["value"]} = {item["points_awarded"]}/{item["max_points"]} pts')
