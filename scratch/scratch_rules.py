import json

def generate_rules_code():
    code = '''
def get_scoring_rules(valuation_data: dict, metrics: dict) -> dict:
    industry = (metrics.get('industry') or valuation_data.get('industry') or "").lower()
    sector = (metrics.get('sector') or valuation_data.get('sector') or "").lower()

    is_bank = ('bank' in industry or 'savings' in industry)
    is_financial = 'financial' in sector
    is_insurance = 'insurance' in industry
    is_reit = 'real estate' in sector or 'reit' in sector
    is_energy = 'energy' in sector or 'basic materials' in sector or 'materials' in sector
    is_utilities = 'utilities' in sector or 'telecommunication' in sector or 'telecom' in industry
    is_defensive = 'consumer defensive' in sector or 'staples' in sector or 'healthcare' in sector or 'health care' in sector
    is_tech = 'technology' in sector or 'communication services' in sector or 'software' in industry or 'internet' in industry or 'information services' in industry

    is_payment_network = False
    is_fintech = False
    if is_financial:
        fintech_gross_profit = metrics.get('fintech_gross_profit')
        if fintech_gross_profit is not None and fintech_gross_profit > 0 and industry == 'credit services':
            is_payment_network = True
        else:
            if industry == 'credit services':
                is_fintech = True
            elif is_bank:
                summary = str(metrics.get('business_summary') or "").lower()
                if "digital banking" in summary or "neobank" in summary or "digital platform" in summary:
                    is_fintech = True
                    is_bank = False

    market_cap = metrics.get('market_cap') or valuation_data.get('market_cap')
    try:
        market_cap = float(market_cap) if market_cap is not None else 0.0
    except:
        market_cap = 0.0
    is_mega_cap = market_cap > 100e9

    raw_fwd_pe = metrics.get('forward_pe') or metrics.get('fwd_pe')
    trigger_pe = 0
    try:
        if raw_fwd_pe is not None and str(raw_fwd_pe).strip() != "":
            f_val = float(str(raw_fwd_pe).replace('%', '').replace('x', '').replace('$', '').replace(',', ''))
            trigger_pe = f_val
    except:
        pass

    rev_2y_g = metrics.get('rev_cagr_2y') or metrics.get('revenue_growth')
    try: rev_2y_g = float(str(rev_2y_g).replace('%','')) if rev_2y_g else 0.0
    except: rev_2y_g = 0.0

    rev_1y_g = metrics.get('forward_revenue_growth') or metrics.get('fwd_rev_growth')
    try: rev_1y_g = float(str(rev_1y_g).replace('%','')) if rev_1y_g else 0.0
    except: rev_1y_g = 0.0

    trigger_rev_g = rev_1y_g if rev_1y_g > 0 else rev_2y_g
    is_high_growth = False
    if (trigger_pe <= 0 or trigger_pe > 80) and trigger_rev_g > 15.0 and not is_bank and not is_insurance and not is_reit:
        is_high_growth = True

    h_rules = []
    b_rules = []

    # HEALTH RULES
    if is_fintech:
        h_rules = [
            {"name": "Bank Leverage (Assets/Eq)", "criteria": ["7.0 - 12.0 => 20p", "6.0-7.0 or 12.0-15.0 => 10p", "Other => 0p"]},
            {"name": "Efficiency Ratio", "criteria": ["< 55% => 20p", "55% - 70% => 10p", "> 70% => 0p"]},
            {"name": "ROA", "criteria": ["> 1.5% => 20p", "0.5% - 1.5% => 10p", "< 0.5% => 0p"]},
            {"name": "ROE", "criteria": ["> 15% => 20p", "5% - 15% => 10p", "< 5% => 0p"]},
            {"name": "NIM", "criteria": ["> 4.0% => 20p", "2.5% - 4.0% => 10p", "< 2.5% => 0p"]}
        ]
    elif is_financial and is_bank:
        h_rules = [
            {"name": "Net Interest Margin", "criteria": ["> 2.8% => 10p", "2.0% - 2.8% => 5p", "< 2.0% => 0p"]},
            {"name": "Efficiency Ratio", "criteria": ["< 55% => 10p", "55% - 65% => 5p", "> 65% => 0p"]},
            {"name": "CET1 Ratio", "criteria": [">= 12% => 20p", "10% - 12% => 10p", "< 10% => 0p"]},
            {"name": "ROE", "criteria": ["> 15% => 20p", "8% - 15% => 10p", "< 8% => 0p"]},
            {"name": "ROA", "criteria": [">= 1.0% => 20p", "0.5% - 1.0% => 10p", "< 0.5% => 0p"]},
            {"name": "BVPS Growth", "criteria": ["> 8% => 20p", "3% - 8% => 10p", "< 3% => 0p"]}
        ]
    elif is_insurance:
        h_rules = [
            {"name": "Float / Net Interest", "criteria": ["> 3.0% => 20p", "1.5% - 3.0% => 10p", "< 1.5% => 0p"]},
            {"name": "Debt-to-Equity", "criteria": ["< 1.0 => 20p", "1.0 - 2.0 => 10p", "> 2.0 => 0p"]},
            {"name": "ROE", "criteria": ["> 12% => 20p", "8% - 12% => 10p", "< 8% => 0p"]},
            {"name": "ROA", "criteria": [">= 1.0% => 20p", "0.5% - 1.0% => 10p", "< 0.5% => 0p"]},
            {"name": "BVPS Growth", "criteria": ["> 8% => 20p", "3% - 8% => 10p", "< 3% => 0p"]}
        ]
    elif is_reit:
        h_rules = [
            {"name": "Debt-to-EBITDA", "criteria": ["< 6.0 => 25p", "6.0 - 7.5 => 12.5p", "> 7.5 => 0p"]},
            {"name": "Interest Coverage", "criteria": ["> 3.0 => 25p", "1.5 - 3.0 => 12.5p", "< 1.5 => 0p"]},
            {"name": "Current Ratio", "criteria": [">= 0.8 => 25p", "< 0.8 => 0p"]},
            {"name": "Dividend Track Record", "criteria": ["> 10 years => 25p", "5 - 10 years => 12.5p", "< 5 years => 0p"]}
        ]
    elif is_energy:
        h_rules = [
            {"name": "Debt-to-Equity", "criteria": ["< 0.6 => 20p", "0.6 - 1.0 => 10p", "> 1.0 => 0p"]},
            {"name": "Current Ratio", "criteria": [">= 1.5 => 20p", "1.0 - 1.5 => 10p", "< 1.0 => 0p"]},
            {"name": "ROE", "criteria": ["> 15% => 20p", "8% - 15% => 10p", "< 8% => 0p"]},
            {"name": "ROIC", "criteria": ["> 12% => 25p", "7% - 12% => 12.5p", "< 7% => 0p"]},
            {"name": "FCF Trend", "criteria": ["Growing => 15p", "Other => 0p"]}
        ]
    elif is_utilities:
        h_rules = [
            {"name": "Debt-to-Equity", "criteria": ["<= 2.0 => 20p", "2.0 - 3.0 => 10p", "> 3.0 => 0p"]},
            {"name": "Current Ratio", "criteria": [">= 0.7 => 20p", "0.5 - 0.7 => 10p", "< 0.5 => 0p"]},
            {"name": "Interest Coverage", "criteria": ["> 3.0 => 20p", "1.5 - 3.0 => 10p", "< 1.5 => 0p"]},
            {"name": "ROE", "criteria": ["> 10% => 20p", "6% - 10% => 10p", "< 6% => 0p"]},
            {"name": "ROIC", "criteria": ["> 6% => 20p", "4% - 6% => 10p", "< 4% => 0p"]}
        ]
    elif is_defensive:
        h_rules = [
            {"name": "Debt-to-Equity", "criteria": ["< 1.0 => 20p", "1.0 - 1.5 => 10p", "> 1.5 => 0p"]},
            {"name": "Current Ratio", "criteria": [">= 1.2 => 20p", "0.9 - 1.2 => 10p", "< 0.9 => 0p"]},
            {"name": "Interest Coverage", "criteria": ["> 5.0 => 20p", "3.0 - 5.0 => 10p", "< 3.0 => 0p"]},
            {"name": "ROE", "criteria": ["> 15% => 20p", "10% - 15% => 10p", "< 10% => 0p"]},
            {"name": "ROIC", "criteria": ["> 12% => 20p", "8% - 12% => 10p", "< 8% => 0p"]}
        ]
    elif is_tech:
        h_rules = [
            {"name": "Debt-to-Equity", "criteria": ["<= 1.0 => 20p", "1.0 - 2.0 => 10p", "> 2.0 => 0p"]},
            {"name": "Current Ratio", "criteria": [">= 1.0 => 20p", "0.8 - 1.0 => 10p", "< 0.8 => 0p"]},
            {"name": "Interest Coverage", "criteria": ["> 5.0 => 20p", "3.0 - 5.0 => 10p", "< 3.0 => 0p"]},
            {"name": "ROE", "criteria": ["> 15% => 20p", "10% - 15% => 10p", "< 10% => 0p"]},
            {"name": "ROIC", "criteria": ["> 15% => 20p", "10% - 15% => 10p", "< 10% => 0p"]}
        ]
    else:
        h_rules = [
            {"name": "Debt-to-Equity", "criteria": ["< 1.0 => 20p", "1.0 - 1.5 => 10p", "> 1.5 => 0p"]},
            {"name": "Current Ratio", "criteria": [">= 1.2 => 20p", "1.0 - 1.2 => 10p", "< 1.0 => 0p"]},
            {"name": "Interest Coverage", "criteria": ["> 4.0 => 20p", "2.0 - 4.0 => 10p", "< 2.0 => 0p"]},
            {"name": "ROE", "criteria": ["> 12% => 20p", "8% - 12% => 10p", "< 8% => 0p"]},
            {"name": "ROIC", "criteria": ["> 10% => 20p", "6% - 10% => 10p", "< 6% => 0p"]}
        ]

    # BUY RULES
    mos_criteria = ["Margin of Safety calculation depends on company's moat (ROIC > 20% & Health > 70/100).", "Strong Moat: > 15% => Max, > 0% => High, > -15% => Half.", "No Moat: > 15% => Max, > 5% => High, > -5% => Half."]
    growth_mega = ["Mega Cap (>$100B): >= 15% => Max, 10-15% => High, 5-10% => Half"]
    growth_std = ["Standard: >= 20% => Max, 15-20% => High, 10-15% => Half, 5-10% => Low"]
    growth_criteria = growth_mega if is_mega_cap else growth_std

    if is_high_growth:
        b_rules = [
            {"name": "Rule of 40 (Growth + Margin)", "criteria": [">= 40 => 30p", "30 - 40 => 15p", "< 30 => 0p"]},
            {"name": "EV/Gross Profit (1Y Fwd)", "criteria": ["<= Sector/Hist => 25p", "<= Target*1.3 => 12.5p", "Higher => 0p"]},
            {"name": "Gross Margin Trend", "criteria": [">= +2.0% => 25p", "-2.0% to +2.0% => 10p", "< -2.0% => 0p"]},
            {"name": "Quick Ratio", "criteria": [">= 1.5 => 20p", "1.0 - 1.5 => 10p", "< 1.0 => 0p"]}
        ]
    else:
        if is_fintech:
            b_rules = [
                {"name": "Margin of Safety", "criteria": mos_criteria},
                {"name": "Revenue Growth (Fwd)", "criteria": growth_criteria},
                {"name": "P/E Ratio (1Y Fwd)", "criteria": ["<= 25 => 20p", "25 - 40 => 10p", "> 40 => 0p"]},
                {"name": "Price-to-Book", "criteria": ["<= 3.5 => 15p", "3.5 - 6.0 => 7.5p", "> 6.0 => 0p"]},
                {"name": "PEG Ratio (Fwd)", "criteria": ["<= 1.2 => 15p", "1.2 - 2.0 => 7.5p", "> 2.0 => 0p"]}
            ]
        elif is_financial and is_bank:
            b_rules = [
                {"name": "Margin of Safety (DDM)", "criteria": mos_criteria},
                {"name": "EPS Growth (Fwd)", "criteria": ["> 7.0% => 10p", "3.0% - 7.0% => 5p", "< 3.0% => 0p"]},
                {"name": "P/E Ratio (1Y Fwd)", "criteria": ["<= Target => 20p", "<= Target*1.3 => 10p", "Higher => 0p", "Monopoly (Moat): Tolerates up to 10% premium for max pts."]},
                {"name": "Price-to-Book", "criteria": ["<= Target => 20p", "<= Target*1.3 => 10p", "Higher => 0p"]},
                {"name": "Dividend Yield (Fwd)", "criteria": ["> 3.0% => 15p", "1.5% - 3.0% => 7.5p", "< 1.5% => 0p"]},
                {"name": "Dividend Payout Ratio", "criteria": ["20% - 40% => 10p", "10-20% or 40-60% => 5p", "Other => 0p"]}
            ]
        elif is_insurance:
            b_rules = [
                {"name": "Margin of Safety", "criteria": mos_criteria},
                {"name": "P/E Ratio (1Y Fwd)", "criteria": ["<= Target => 20p", "<= Target*1.3 => 10p", "Higher => 0p"]},
                {"name": "Price-to-Book", "criteria": ["<= Target => 25p", "<= Target*1.3 => 12.5p", "Higher => 0p"]},
                {"name": "Dividend Yield (Fwd)", "criteria": ["> 3.0% => 15p", "1.5% - 3.0% => 7.5p", "< 1.5% => 0p"]},
                {"name": "EPS Growth (Fwd)", "criteria": growth_criteria}
            ]
        elif is_reit:
            b_rules = [
                {"name": "Margin of Safety (NAV)", "criteria": mos_criteria},
                {"name": "AFFO/EPS Growth (Fwd)", "criteria": growth_criteria},
                {"name": "P/AFFO or P/OCF or EV/EBITDA", "criteria": ["<= Target => 20p", "<= Target*1.3 => 10p", "Higher => 0p"]},
                {"name": "AFFO/FCF Yield (Fwd)", "criteria": ["> 8% => 15p", "5% - 8% => 7.5p", "< 5% => 0p"]},
                {"name": "Dividend Yield (Fwd)", "criteria": ["> 5% => 15p", "3% - 5% => 7.5p", "< 3% => 0p"]}
            ]
        elif is_energy:
            b_rules = [
                {"name": "Margin of Safety", "criteria": mos_criteria},
                {"name": "Price-to-Book (TTM)", "criteria": ["<= Target => 30p", "<= Target*1.3 => 15p", "Higher => 0p"]},
                {"name": "EV/EBITDA (1Y Fwd)", "criteria": ["<= Target => 20p", "<= Target*1.3 => 10p", "Higher => 0p"]},
                {"name": "Dividend Yield (Fwd)", "criteria": ["> 4% => 20p", "2% - 4% => 10p", "< 2% => 0p"]}
            ]
        elif is_utilities:
            b_rules = [
                {"name": "Margin of Safety", "criteria": mos_criteria},
                {"name": "EPS Growth (Fwd)", "criteria": growth_criteria},
                {"name": "P/E Ratio (1Y Fwd)", "criteria": ["<= Target => 15p", "<= Target*1.3 => 7.5p", "Higher => 0p"]},
                {"name": "EV/EBITDA (1Y Fwd)", "criteria": ["<= Target => 20p", "<= Target*1.3 => 10p", "Higher => 0p"]},
                {"name": "Dividend Yield (Fwd)", "criteria": ["> 4.0% => 25p", "2.5% - 4.0% => 12.5p", "< 2.5% => 0p"]}
            ]
        elif is_defensive:
            b_rules = [
                {"name": "Margin of Safety", "criteria": mos_criteria},
                {"name": "EPS Growth (Fwd)", "criteria": growth_criteria},
                {"name": "P/E Ratio (1Y Fwd)", "criteria": ["<= Target => 20p", "<= Target*1.3 => 10p", "Higher => 0p"]},
                {"name": "EV/EBITDA (1Y Fwd)", "criteria": ["<= Target => 15p", "<= Target*1.3 => 7.5p", "Higher => 0p"]},
                {"name": "PEG Ratio (Fwd)", "criteria": ["<= Target => 20p", "<= Target*1.3 => 10p", "Higher => 0p"]}
            ]
        elif is_tech:
            b_rules = [
                {"name": "Margin of Safety (DCF)", "criteria": mos_criteria},
                {"name": "Revenue Growth (2y Avg Fwd)", "criteria": growth_criteria},
                {"name": "P/E Ratio (1Y Fwd)", "criteria": ["<= Target => 20p", "<= Target*1.3 => 10p", "Higher => 0p"]},
                {"name": "EV/EBITDA (1Y Fwd)", "criteria": ["<= Target => 10p", "<= Target*1.3 => 5p", "Higher => 0p"]},
                {"name": "PEG Ratio (Fwd)", "criteria": ["<= Target => 10p", "<= Target*1.3 => 5p", "Higher => 0p"]},
                {"name": "P/S Ratio (1Y Fwd)", "criteria": ["<= Target => 10p", "<= Target*1.3 => 5p", "Higher => 0p"]}
            ]
        else:
            b_rules = [
                {"name": "Margin of Safety", "criteria": mos_criteria},
                {"name": "Revenue Growth (2y Avg Fwd)", "criteria": growth_criteria},
                {"name": "P/E Ratio (1Y Fwd)", "criteria": ["<= Target => 20p", "<= Target*1.3 => 10p", "Higher => 0p"]},
                {"name": "EV/EBITDA (1Y Fwd)", "criteria": ["<= Target => 15p", "<= Target*1.3 => 7.5p", "Higher => 0p"]},
                {"name": "PEG Ratio (Fwd)", "criteria": ["<= Target => 15p", "<= Target*1.3 => 7.5p", "Higher => 0p"]}
            ]

    return {
        "health_rules": h_rules,
        "buy_rules": b_rules
    }
'''
    return code

print(generate_rules_code())
