import re
import sys

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Replace get_peer_stats block
    old_peer_stats = '''        if peers_data:
            def get_peer_stats(key):
                vals = []
                for p in peers_data:
                    v = p.get(key)
                    if v is not None and isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
                        vals.append(float(v))
                if not vals:
                    return None, None
                return statistics.median(vals), sum(vals) / len(vals)

            _, mean_peer_pe = get_peer_stats('pe_ratio')
            median_peer_pfcf, mean_peer_pfcf = get_peer_stats('pfcf_ratio')
            median_peer_ps, mean_peer_ps = get_peer_stats('ps_ratio')
            median_peer_pb, mean_peer_pb = get_peer_stats('price_to_book')
            median_peer_ev_ebitda, mean_peer_ev_ebitda = get_peer_stats('ev_to_ebitda')'''

    new_peer_stats = '''        # Strict Forward Proxy Functions
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

        # Enhance peers_data with Forward metrics
        if peers_data:
            for p in peers_data:
                p['forward_ev_sales'] = calculateForwardEvSales(p)
                p['forward_ev_ebitda'] = calculateForwardEvEbitda(p)
                p['forward_pe'] = calculateForwardPE(p)

            # Clean Median Rule
            def get_clean_median(key):
                vals = []
                for p in peers_data:
                    v = p.get(key)
                    if v is not None and isinstance(v, (int, float)) and math.isfinite(v) and v > 0:
                        vals.append(float(v))
                if not vals:
                    return None
                return statistics.median(vals)

            median_peer_pe = get_clean_median('forward_pe')
            median_peer_ps = get_clean_median('forward_ev_sales')
            median_peer_ev_ebitda = get_clean_median('forward_ev_ebitda')
            median_peer_pb = get_clean_median('price_to_book') # Keep PB for Financials
        else:
            median_peer_pe = None
            median_peer_ps = None
            median_peer_ev_ebitda = None
            median_peer_pb = None'''
    
    if old_peer_stats in content:
        content = content.replace(old_peer_stats, new_peer_stats)
    else:
        print(f"Warning: old_peer_stats not found in {filepath}")

    # 2. Replace Relative Valuation Multi-Metric Block
    old_rv_block = '''        # Multi-Metric Sector-Weighted Relative Valuation
        company_eps = eps_for_valuation or 0
        company_shares = data.get("shares_outstanding") or 1
        
        company_fcf_val = data.get("fcf") or 0
        company_fcf_share = (company_fcf_val / company_shares) if company_fcf_val and company_shares else 0
        
        company_sales_val = data.get("revenue") or 0
        company_sales_share = (company_sales_val / company_shares) if company_sales_val and company_shares else 0
        
        company_book_val = data.get("book_value") or (data.get("book_value_per_share") * company_shares if data.get("book_value_per_share") and company_shares else 0)
        company_book_share = (company_book_val / company_shares) if company_book_val and company_shares else (data.get("book_value_per_share") or 0)
        
        company_ebitda = data.get("ebitda") or 0
        company_debt = data.get("total_debt") or 0
        company_cash = data.get("total_cash") or 0

        relative_variant = overrides_inputs.get("relative-variant", "peers")
        defaults = { "PE": 20.0, "PFCF": 20.0, "PS": 2.0, "PB": 2.0, "EV_EBITDA": 12.0 }
        
        if relative_variant == "peers":
            bPE = median_peer_pe if median_peer_pe is not None else defaults["PE"]
            bPFCF = median_peer_pfcf if median_peer_pfcf is not None else defaults["PFCF"]
            bPS = median_peer_ps if median_peer_ps is not None else defaults["PS"]
            bPB = median_peer_pb if median_peer_pb is not None else defaults["PB"]
            bEVEBITDA = median_peer_ev_ebitda if median_peer_ev_ebitda is not None else defaults["EV_EBITDA"]
        elif relative_variant == "average":
            bPE = mean_peer_pe if mean_peer_pe is not None else defaults["PE"]
            bPFCF = mean_peer_pfcf if mean_peer_pfcf is not None else defaults["PFCF"]
            bPS = mean_peer_ps if mean_peer_ps is not None else defaults["PS"]
            bPB = mean_peer_pb if mean_peer_pb is not None else defaults["PB"]
            bEVEBITDA = mean_peer_ev_ebitda if mean_peer_ev_ebitda is not None else defaults["EV_EBITDA"]
        else: # sp500
            bPE = 24.5
            bPFCF = 28.0
            bPS = 2.8
            bPB = 4.5
            bEVEBITDA = 15.0

        fvPE = company_eps * bPE
        fvPFCF = company_fcf_share * bPFCF
        fvPS = company_sales_share * bPS
        fvPB = company_book_share * bPB
        
        impliedEV = company_ebitda * bEVEBITDA
        impliedMktCap = impliedEV - company_debt + company_cash
        fvEVEBITDA = impliedMktCap / company_shares if company_shares > 0 else 0

        SECTOR_WEIGHTS = {
            'Technology': { "PE": 0.35, "EV_EBITDA": 0.50, "PS": 0.15 },
            'Information Technology': { "PE": 0.35, "EV_EBITDA": 0.50, "PS": 0.15 },
            'Technology_Growth': { "PE": 0.00, "EV_EBITDA": 0.20, "PS": 0.80 },
            'Financial Services': { "PE": 0.40, "PB": 0.60 },
            'Financials': { "PE": 0.40, "PB": 0.60 },
            'Industrials': { "PE": 0.20, "EV_EBITDA": 0.80 },
            'Energy': { "PE": 0.20, "EV_EBITDA": 0.80 },
            'Consumer Defensive': { "PE": 0.50, "EV_EBITDA": 0.30, "PS": 0.20 },
            'Consumer Staples': { "PE": 0.50, "EV_EBITDA": 0.30, "PS": 0.20 },
            'Consumer Cyclical': { "PE": 0.35, "EV_EBITDA": 0.35, "PS": 0.30 },
            'Consumer Discretionary': { "PE": 0.35, "EV_EBITDA": 0.35, "PS": 0.30 },
            'Healthcare': { "PE": 0.35, "EV_EBITDA": 0.40, "PS": 0.25 },
            'Health Care': { "PE": 0.35, "EV_EBITDA": 0.40, "PS": 0.25 },
            'Communication Services': { "PE": 0.35, "EV_EBITDA": 0.40, "PS": 0.25 },
            'Utilities': { "PE": 0.50, "EV_EBITDA": 0.50 },
            'Basic Materials': { "PE": 0.25, "EV_EBITDA": 0.75 },
            'Materials': { "PE": 0.25, "EV_EBITDA": 0.75 },
            'Real Estate': { "PE": 0.00, "P_FFO": 0.80, "P_AFFO": 0.20 },
            'Default': { "PE": 0.40, "EV_EBITDA": 0.40, "PS": 0.20 }
        }

        sector_name = sector or 'Default'
        weights = SECTOR_WEIGHTS.get(sector_name) or SECTOR_WEIGHTS.get('Default')
        
        if (sector_name == 'Technology' or sector_name == 'Information Technology') and (company_eps <= 0 or company_ebitda <= 0 or bPE > 50):
            weights = SECTOR_WEIGHTS['Technology_Growth']
            
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
                safeVal = val if (val is not None and math.isfinite(val) and val > 0) else 0
                if safeVal > 0:
                    weightedSum += safeVal * w
                    totalWeight += w

        if weights.get("PE") is not None: calcMetric(fvPE, weights.get("PE"))
        if weights.get("PFCF") is not None: calcMetric(fvPFCF, weights.get("PFCF"))
        if weights.get("PS") is not None: calcMetric(fvPS, weights.get("PS"))
        if weights.get("PB") is not None: calcMetric(fvPB, weights.get("PB"))
        if weights.get("EV_EBITDA") is not None: calcMetric(fvEVEBITDA, weights.get("EV_EBITDA"))
        if weights.get("P_FFO") is not None: calcMetric(fvPE, weights.get("P_FFO"))
        if weights.get("P_AFFO") is not None: calcMetric(fvPFCF, weights.get("P_AFFO"))

        if totalWeight > 0:
            relative_value = weightedSum / totalWeight
        else:
            relative_value = fvPE if fvPE > 0 else (fvPS if fvPS > 0 else None)'''

    new_rv_block = '''        # Multi-Metric Sector-Weighted Relative Valuation (Strict Forward)
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
        
        # We need EV = MCAP + Debt - Cash
        # But we want to find Fair Value (Implied Price), so we use the Median Multiples
        
        bPE = median_peer_pe # Forward PE
        bEVSALES = median_peer_ps # Forward EV/Sales
        bEVEBITDA = median_peer_ev_ebitda # Forward EV/EBITDA
        bPB = median_peer_pb # Current P/B for Financials
        
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
            'Technology_Growth': { "PE": 0.00, "EV_EBITDA": 0.00, "EV_SALES": 1.00 }, # Handled dynamically below
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
        # If Forward PE is null or <= 0, move weight entirely to Forward EV/Sales
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
                # Strictly evaluate to None (null) if missing
                if val is not None and math.isfinite(val) and val > 0:
                    weightedSum += val * w
                    totalWeight += w

        if weights.get("PE") is not None: calcMetric(fvPE, weights.get("PE"))
        if weights.get("EV_SALES") is not None: calcMetric(fvEVSALES, weights.get("EV_SALES"))
        if weights.get("EV_EBITDA") is not None: calcMetric(fvEVEBITDA, weights.get("EV_EBITDA"))
        if weights.get("PB") is not None: calcMetric(fvPB, weights.get("PB"))
        
        # Keeping P_FFO and P_AFFO simple approximations if Real Estate
        if weights.get("P_FFO") is not None: calcMetric(fvPE, weights.get("P_FFO"))
        if weights.get("P_AFFO") is not None: calcMetric(fvPE, weights.get("P_AFFO"))

        if totalWeight > 0:
            relative_value = weightedSum / totalWeight
        else:
            relative_value = None'''

    if old_rv_block in content:
        content = content.replace(old_rv_block, new_rv_block)
    else:
        print(f"Warning: old_rv_block not found in {filepath}")

    # Fix peer assignments in relative section of output dict
    old_out_block = '''                "median_peer_pfcf": sanitize(median_peer_pfcf),
                "median_peer_ps": sanitize(median_peer_ps),
                "median_peer_pb": sanitize(median_peer_pb),
                "median_peer_ev_ebitda": sanitize(median_peer_ev_ebitda),
                "median_peer_peg": sanitize(median_peer_peg),
                "mean_peer_pe": sanitize(mean_peer_pe),
                "mean_peer_pfcf": sanitize(mean_peer_pfcf),
                "mean_peer_ps": sanitize(mean_peer_ps),
                "mean_peer_pb": sanitize(mean_peer_pb),
                "mean_peer_ev_ebitda": sanitize(mean_peer_ev_ebitda),'''
                
    new_out_block = '''                "median_peer_pe": sanitize(median_peer_pe), # Forward P/E
                "median_peer_ps": sanitize(median_peer_ps), # Forward EV/Sales
                "median_peer_pb": sanitize(median_peer_pb),
                "median_peer_ev_ebitda": sanitize(median_peer_ev_ebitda), # Forward EV/EBITDA
                "median_peer_peg": sanitize(median_peer_peg),'''

    if old_out_block in content:
        content = content.replace(old_out_block, new_out_block)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Patched {filepath}")

patch_file(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\Calculator-Fair-Value\index.py')
patch_file(r'c:\Users\Snoozie\Downloads\Calculator-Fair-Value\Calculator-Fair-Value\api\index.py')
