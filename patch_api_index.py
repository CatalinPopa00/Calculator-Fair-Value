import re
import sys

filepath = r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\Calculator-Fair-Value\api\index.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Replace the peer dynamic calculations (around line 446)
old_peer_dynamic = '''        # Dynamic peer P/E and PEG calculations using real-time price and EPS
        if peers_data:
            for p in peers_data:
                p_price = p.get("price")
                p_eps = p.get("eps")
                if p_price and p_eps and p_eps > 0:
                    p["pe_ratio"] = p_price / p_eps
                p_pe = p.get("pe_ratio")
                p_growth = p.get("earnings_growth") or p.get("revenue_growth")
                if p_pe and p_growth and p_growth > 0:
                    p["peg_ratio"] = p_pe / (p_growth * 100.0)'''

new_peer_dynamic = '''        # Strict Forward Proxy Functions
        def calculateForwardEvSales(comp_data):
            mcap = comp_data.get("market_cap") or 0
            debt = comp_data.get("total_debt") or 0
            cash = comp_data.get("total_cash") or 0
            curr_ev = mcap + debt - cash
            fwd_rev = comp_data.get("forward_revenue")
            if fwd_rev is None or fwd_rev <= 0:
                rev = comp_data.get("revenue")
                g = comp_data.get("revenue_growth")
                if rev and g is None and comp_data.get("next_3y_rev_growth"):
                    g = comp_data.get("next_3y_rev_growth")
                if rev and rev > 0 and g is not None:
                    fwd_rev = rev * (1 + g)
            if fwd_rev is None or fwd_rev <= 0:
                return None
            val = curr_ev / fwd_rev
            return val if val > 0 else None

        def calculateForwardEvEbitda(comp_data):
            mcap = comp_data.get("market_cap") or 0
            debt = comp_data.get("total_debt") or 0
            cash = comp_data.get("total_cash") or 0
            curr_ev = mcap + debt - cash
            fwd_eps = comp_data.get("forward_eps") or comp_data.get("eps")
            shares = comp_data.get("shares_outstanding")
            if not shares or shares <= 0:
                price = comp_data.get("price")
                if mcap and price and price > 0:
                    shares = mcap / price
            if not fwd_eps or not shares or shares <= 0:
                return None
            fwd_ni = fwd_eps * shares
            ebitda = comp_data.get("ebitda") or 0
            ni = comp_data.get("net_income") or 0
            tax_int_da = ebitda - ni
            est_fwd_ebitda = fwd_ni + tax_int_da
            if est_fwd_ebitda <= 0:
                return None
            val = curr_ev / est_fwd_ebitda
            return val if val > 0 else None

        def calculateForwardPE(comp_data):
            fwd_eps = comp_data.get("forward_eps") or comp_data.get("eps")
            price = comp_data.get("price")
            if fwd_eps and price and fwd_eps > 0:
                val = price / fwd_eps
                return val if val > 0 else None
            return None

        # Dynamic peer P/E, PEG, and Forward calculations
        if peers_data:
            for p in peers_data:
                p_price = p.get("price")
                p_eps = p.get("eps")
                if p_price and p_eps and p_eps > 0:
                    p["pe_ratio"] = p_price / p_eps
                p_pe = p.get("pe_ratio")
                p_growth = p.get("earnings_growth") or p.get("revenue_growth")
                if p_pe and p_growth and p_growth > 0:
                    p["peg_ratio"] = p_pe / (p_growth * 100.0)
                
                # Apply proxies for peers
                p['forward_ev_sales'] = calculateForwardEvSales(p)
                p['forward_ev_ebitda'] = calculateForwardEvEbitda(p)
                p['forward_pe'] = calculateForwardPE(p)'''

if old_peer_dynamic in content:
    content = content.replace(old_peer_dynamic, new_peer_dynamic)
else:
    print("WARNING: Could not find old_peer_dynamic in api/index.py")


# 2. Replace the medians block (around line 705-757)
old_medians_block = '''        # Calculate Peer PE stats safely
        median_peer_pe = None
        mean_peer_pe = None
        median_peer_peg = None
        median_peer_pfcf = None
        mean_peer_pfcf = None
        median_peer_ps = None
        mean_peer_ps = None
        median_peer_pb = None
        mean_peer_pb = None
        median_peer_ev_ebitda = None
        mean_peer_ev_ebitda = None
        if peers_data:
            valid_pes = []
            for p in peers_data:
                val = p.get('pe_ratio')
                if val is not None and isinstance(val, (int, float)) and math.isfinite(val) and val > 0:
                    valid_pes.append(float(val))
            
            if valid_pes:
                median_peer_pe = statistics.median(valid_pes)
                mean_peer_pe = sum(valid_pes) / len(valid_pes)
                
            valid_pegs = []
            for p in peers_data:
                if p.get('ticker') == ticker: continue
                val = p.get('peg_ratio')
                if val is not None and isinstance(val, (int, float)) and math.isfinite(val):
                    valid_pegs.append(float(val))
            
            if valid_pegs:
                median_peer_peg = statistics.median(valid_pegs)


            valid_pfcfs = [float(p.get('pfcf_ratio')) for p in peers_data if p.get('pfcf_ratio') and isinstance(p.get('pfcf_ratio'), (int, float)) and math.isfinite(p.get('pfcf_ratio')) and p.get('pfcf_ratio') > 0]
            if valid_pfcfs:
                median_peer_pfcf = statistics.median(valid_pfcfs)
                mean_peer_pfcf = sum(valid_pfcfs) / len(valid_pfcfs)

            valid_ps_list = [float(p.get('ps_ratio')) for p in peers_data if p.get('ps_ratio') and isinstance(p.get('ps_ratio'), (int, float)) and math.isfinite(p.get('ps_ratio')) and p.get('ps_ratio') > 0]
            if valid_ps_list:
                median_peer_ps = statistics.median(valid_ps_list)
                mean_peer_ps = sum(valid_ps_list) / len(valid_ps_list)

            valid_pbs = [float(p.get('price_to_book')) for p in peers_data if p.get('price_to_book') and isinstance(p.get('price_to_book'), (int, float)) and math.isfinite(p.get('price_to_book')) and p.get('price_to_book') > 0]
            if valid_pbs:
                median_peer_pb = statistics.median(valid_pbs)
                mean_peer_pb = sum(valid_pbs) / len(valid_pbs)

            valid_ev_ebitdas = [float(p.get('ev_to_ebitda')) for p in peers_data if p.get('ev_to_ebitda') and isinstance(p.get('ev_to_ebitda'), (int, float)) and math.isfinite(p.get('ev_to_ebitda')) and p.get('ev_to_ebitda') > 0]
            if valid_ev_ebitdas:
                median_peer_ev_ebitda = statistics.median(valid_ev_ebitdas)
                mean_peer_ev_ebitda = sum(valid_ev_ebitdas) / len(valid_ev_ebitdas)'''

new_medians_block = '''        # Clean Median Rule for Peer Stats
        median_peer_pe = None
        mean_peer_pe = None
        median_peer_peg = None
        median_peer_pfcf = None
        mean_peer_pfcf = None
        median_peer_ps = None
        mean_peer_ps = None
        median_peer_pb = None
        mean_peer_pb = None
        median_peer_ev_ebitda = None
        mean_peer_ev_ebitda = None
        
        if peers_data:
            def get_clean_median(key):
                vals = []
                for p in peers_data:
                    v = p.get(key)
                    if v is not None and isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
                        vals.append(float(v))
                if not vals:
                    return None
                return statistics.median(vals)
                
            # Compute Strict Forward Medians
            median_peer_pe = get_clean_median('forward_pe')
            median_peer_ps = get_clean_median('forward_ev_sales')
            median_peer_ev_ebitda = get_clean_median('forward_ev_ebitda')
            median_peer_pb = get_clean_median('price_to_book')
            median_peer_pfcf = get_clean_median('pfcf_ratio')
            
            valid_pegs = []
            for p in peers_data:
                if p.get('ticker') == ticker: continue
                val = p.get('peg_ratio')
                if val is not None and isinstance(val, (int, float)) and math.isfinite(val) and val > 0:
                    valid_pegs.append(float(val))
            if valid_pegs:
                median_peer_peg = statistics.median(valid_pegs)'''

if old_medians_block in content:
    content = content.replace(old_medians_block, new_medians_block)
else:
    print("WARNING: Could not find old_medians_block in api/index.py")


# 3. Replace the calculate_relative_valuation block (around line 550)
old_relative_block = '''        # Relative Valuation (P/E Based currently)
        relative_value = calculate_relative_valuation(ticker, data, peers_data)'''

new_relative_block = '''        # Multi-Metric Sector-Weighted Relative Valuation (Strict Forward)
        company_shares = data.get("shares_outstanding") or 1
        company_debt = data.get("total_debt") or 0
        company_cash = data.get("total_cash") or 0
        company_book_val = data.get("book_value") or (data.get("book_value_per_share") * company_shares if data.get("book_value_per_share") and company_shares else 0)
        company_book_share = (company_book_val / company_shares) if company_book_val and company_shares else (data.get("book_value_per_share") or 0)
        
        # Calculate Target Company Forward Metrics
        targ_fwd_eps = data.get("forward_eps") or data.get("eps")
        targ_fwd_rev = data.get("forward_revenue")
        if targ_fwd_rev is None or targ_fwd_rev <= 0:
            tr = data.get("revenue")
            tg = data.get("next_3y_rev_growth")
            if tr and tr > 0 and tg is not None:
                targ_fwd_rev = tr * (1 + tg)
                
        targ_ebitda = data.get("ebitda") or 0
        targ_ni = data.get("net_income") or (data.get("adjusted_eps") * company_shares if data.get("adjusted_eps") else 0)
        
        bPE = None
        bEVSALES = None
        bEVEBITDA = None
        bPB = None
        
        # We need to compute median beforehand since we extracted the relative logic
        def get_clean_median_local(key):
            vals = []
            if peers_data:
                for p in peers_data:
                    v = p.get(key)
                    if v is not None and isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
                        vals.append(float(v))
            if not vals:
                return None
            return statistics.median(vals)

        bPE = get_clean_median_local('forward_pe')
        bEVSALES = get_clean_median_local('forward_ev_sales')
        bEVEBITDA = get_clean_median_local('forward_ev_ebitda')
        bPB = get_clean_median_local('price_to_book')
        
        # 1. Forward P/E Fair Value
        fvPE = (targ_fwd_eps * bPE) if (targ_fwd_eps and bPE and targ_fwd_eps > 0) else None
        
        # 2. Forward EV/Sales Fair Value
        fvEVSALES = None
        if targ_fwd_rev and bEVSALES and targ_fwd_rev > 0:
            implied_ev_sales = targ_fwd_rev * bEVSALES
            implied_mcap_sales = implied_ev_sales - company_debt + company_cash
            fvEVSALES = implied_mcap_sales / company_shares if company_shares > 0 else None
            if fvEVSALES is not None and fvEVSALES <= 0: fvEVSALES = None

        # 3. Forward EV/EBITDA Fair Value
        fvEVEBITDA = None
        if targ_fwd_eps and company_shares > 0:
            est_fwd_ni = targ_fwd_eps * company_shares
            tax_int_da = targ_ebitda - targ_ni
            est_fwd_ebitda = est_fwd_ni + tax_int_da
            if est_fwd_ebitda > 0 and bEVEBITDA:
                implied_ev_ebitda = est_fwd_ebitda * bEVEBITDA
                implied_mcap_ebitda = implied_ev_ebitda - company_debt + company_cash
                fvEVEBITDA = implied_mcap_ebitda / company_shares if company_shares > 0 else None
                if fvEVEBITDA is not None and fvEVEBITDA <= 0: fvEVEBITDA = None
                
        # 4. Current P/B Fair Value (Financials only)
        fvPB = (company_book_share * bPB) if (company_book_share and bPB and company_book_share > 0) else None

        SECTOR_WEIGHTS = {
            'Technology': { "PE": 0.35, "EV_EBITDA": 0.50, "EV_SALES": 0.15 },
            'Information Technology': { "PE": 0.35, "EV_EBITDA": 0.50, "EV_SALES": 0.15 },
            'Technology_Growth': { "PE": 0.00, "EV_EBITDA": 0.00, "EV_SALES": 1.00 },
            'Financial Services': { "PE": 0.40, "PB": 0.60 },
            'Financials': { "PE": 0.40, "PB": 0.60 },
            'Industrials': { "PE": 0.20, "EV_EBITDA": 0.80 },
            'Energy': { "PE": 0.20, "EV_EBITDA": 0.80 },
            'Consumer Defensive': { "PE": 0.50, "EV_EBITDA": 0.30, "EV_SALES": 0.20 },
            'Consumer Staples': { "PE": 0.50, "EV_EBITDA": 0.30, "EV_SALES": 0.20 },
            'Consumer Cyclical': { "PE": 0.35, "EV_EBITDA": 0.35, "EV_SALES": 0.30 },
            'Consumer Discretionary': { "PE": 0.35, "EV_EBITDA": 0.35, "EV_SALES": 0.30 },
            'Healthcare': { "PE": 0.35, "EV_EBITDA": 0.40, "EV_SALES": 0.25 },
            'Health Care': { "PE": 0.35, "EV_EBITDA": 0.40, "EV_SALES": 0.25 },
            'Communication Services': { "PE": 0.35, "EV_EBITDA": 0.40, "EV_SALES": 0.25 },
            'Utilities': { "PE": 0.50, "EV_EBITDA": 0.50 },
            'Basic Materials': { "PE": 0.25, "EV_EBITDA": 0.75 },
            'Materials': { "PE": 0.25, "EV_EBITDA": 0.75 },
            'Real Estate': { "PE": 0.00, "P_FFO": 0.80, "P_AFFO": 0.20 },
            'Default': { "PE": 0.40, "EV_EBITDA": 0.40, "EV_SALES": 0.20 }
        }

        sector_name = sector or 'Default'
        weights = SECTOR_WEIGHTS.get(sector_name) or SECTOR_WEIGHTS.get('Default')
        
        # Dynamic Technology_Growth rule:
        if (sector_name == 'Technology' or sector_name == 'Information Technology') and (not targ_fwd_eps or targ_fwd_eps <= 0 or not bPE or bPE > 50):
            weights = { "PE": 0.00, "EV_SALES": 1.00 }
            
        if sector_name not in SECTOR_WEIGHTS:
            if 'Tech' in sector_name: weights = SECTOR_WEIGHTS['Technology']
            elif 'Finance' in sector_name or 'Bank' in sector_name: weights = SECTOR_WEIGHTS['Financial Services']
            elif 'Industrial' in sector_name: weights = SECTOR_WEIGHTS['Industrials']
            elif 'Energy' in sector_name: weights = SECTOR_WEIGHTS['Energy']
            elif 'Health' in sector_name: weights = SECTOR_WEIGHTS['Healthcare']
            elif 'Real Estate' in sector_name or 'REIT' in sector_name: weights = SECTOR_WEIGHTS['Real Estate']
            elif 'Communication' in sector_name: weights = SECTOR_WEIGHTS['Communication Services']
            elif 'Utilit' in sector_name: weights = SECTOR_WEIGHTS['Utilities']
            elif 'Material' in sector_name: weights = SECTOR_WEIGHTS['Materials']

        weightedSum = 0.0
        totalWeight = 0.0
        
        def calcMetric(val, w):
            nonlocal weightedSum, totalWeight
            if w is not None and w > 0:
                if val is not None and math.isfinite(val) and val > 0:
                    weightedSum += val * w
                    totalWeight += w

        if weights.get("PE") is not None: calcMetric(fvPE, weights.get("PE"))
        if weights.get("EV_SALES") is not None: calcMetric(fvEVSALES, weights.get("EV_SALES"))
        if weights.get("EV_EBITDA") is not None: calcMetric(fvEVEBITDA, weights.get("EV_EBITDA"))
        if weights.get("PB") is not None: calcMetric(fvPB, weights.get("PB"))
        
        if weights.get("P_FFO") is not None: calcMetric(fvPE, weights.get("P_FFO"))
        if weights.get("P_AFFO") is not None: calcMetric(fvPE, weights.get("P_AFFO"))

        if totalWeight > 0:
            relative_value = weightedSum / totalWeight
        else:
            relative_value = None'''

if old_relative_block in content:
    content = content.replace(old_relative_block, new_relative_block)
else:
    print("WARNING: Could not find old_relative_block in api/index.py")


with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Patched {filepath}")
