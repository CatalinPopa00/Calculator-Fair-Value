import re

with open("models/scoring.py", "r", encoding="utf-8") as f:
    content = f.read()

helpers = """
    def get_pe_pts(pe_val, fwd_g, rev_fwd_g):
        if pe_val is None or pe_val <= 0: return 0
        if is_monopoly and hist_pe and hist_pe > 0:
            discount = ((hist_pe - pe_val) / hist_pe) * 100.0
            if discount >= 25.0: return 20
            elif discount >= 15.0: return 15
            elif discount >= 10.0: return 10
            elif discount > 0.0: return 5
            return 0
        elif is_fintech:
            return 20 if pe_val <= 25 else (10 if pe_val <= 40 else 0)
        elif is_financial and is_bank:
            return 20 if pe_val <= 13 else (10 if pe_val <= 15 else 0)
        elif is_insurance:
            return 20 if pe_val <= 15 else (10 if pe_val <= 18 else 0)
        elif is_energy:
            return 5 if pe_val < 6 else (15 if pe_val <= 15 else (10 if pe_val <= 20 else 0))
        elif is_utilities:
            return 15 if pe_val <= 15 else (7.5 if pe_val <= 18 else 0)
        elif is_defensive:
            pts = 20 if pe_val <= 20 else (10 if pe_val <= 25 else 0)
            if pts == 0 and fwd_g is not None and fwd_g > 0:
                peg = pe_val / fwd_g
                if 0 < peg <= 1.2 and fwd_g >= 15.0: pts = 10
            return pts
        elif is_tech:
            pts = 20 if pe_val <= 25.0 else (10 if pe_val <= 32.5 else 0)
            if pts == 0 and fwd_g is not None and fwd_g > 0:
                peg = pe_val / fwd_g
                if 0 < peg <= 1.2 and rev_fwd_g >= 20.0: pts = 10
            return pts
        elif is_payment_network:
            return 20 if pe_val <= 28 else (10 if pe_val <= 35 else 0)
        else:
            pts = 20 if pe_val <= 18 else (10 if pe_val <= 22 else 0)
            if pts == 0 and fwd_g is not None and fwd_g > 0:
                peg = pe_val / fwd_g
                if 0 < peg <= 1.2 and rev_fwd_g >= 15.0: pts = 10
            return pts

    def get_ev_ebitda_pts(ev_val, pe_val, fwd_g, rev_fwd_g):
        if ev_val is None or ev_val <= 0: return 0
        if is_energy:
            return 20 if ev_val <= 6.0 else (10 if ev_val <= 9.0 else 0)
        elif is_utilities:
            return 20 if ev_val <= 10.0 else (10 if ev_val <= 14.0 else 0)
        elif is_defensive:
            pts = 15 if ev_val <= 14.0 else (7.5 if ev_val <= 18.0 else 0)
            if pts == 0 and pe_val and pe_val > 0 and fwd_g and fwd_g > 0:
                peg = pe_val / fwd_g
                if 0 < peg <= 1.2 and fwd_g >= 15.0: pts = 7.5
            return pts
        elif is_tech:
            pts = 10 if ev_val <= 18.0 else (5 if ev_val <= 25.0 else 0)
            if pts == 0 and pe_val and pe_val > 0 and fwd_g and fwd_g > 0:
                peg = pe_val / fwd_g
                if 0 < peg <= 1.2 and rev_fwd_g >= 20.0: pts = 5
            return pts
        elif is_payment_network:
            return 15 if ev_val <= 20.0 else (7.5 if ev_val <= 25.0 else 0)
        else:
            pts = 15 if ev_val <= 12.0 else (7.5 if ev_val <= 16.0 else 0)
            if pts == 0 and pe_val and pe_val > 0 and fwd_g and fwd_g > 0:
                peg = pe_val / fwd_g
                if 0 < peg <= 1.2 and rev_fwd_g >= 15.0: pts = 5
            return pts

    def get_pb_pts(pb_val):
        if pb_val is None or pb_val <= 0: return 0
        if is_fintech:
            return 15 if pb_val <= 3.5 else (7.5 if pb_val <= 6.0 else 0)
        elif is_financial and is_bank:
            return 20 if pb_val < 1.5 else (10 if pb_val <= 2.0 else 0)
        elif is_insurance:
            return 25 if pb_val < 1.5 else (12.5 if pb_val <= 2.0 else 0)
        elif is_energy:
            return 20 if pb_val <= 1.5 else (10 if pb_val <= 2.5 else 0)
        else:
            return 10 if pb_val <= 2.0 else (5 if pb_val <= 3.0 else 0)

    def get_peg_pts(peg_v, pe_val, fwd_g):
        if peg_v is None or peg_v <= 0:
            peg_v = clean_ratio(metrics.get("peg_ratio"))
            if (peg_v is None or peg_v <= 0) and pe_val and pe_val > 0 and fwd_g and fwd_g > 0:
                peg_v = pe_val / fwd_g
        if peg_v is None or peg_v <= 0: return 0
        if is_fintech: return 15 if peg_v <= 1.2 else (7.5 if peg_v <= 2.0 else 0)
        elif is_payment_network: return 15 if peg_v <= 1.6 else (7.5 if peg_v <= 2.2 else 0)
        elif is_defensive: return 20 if peg_v < 1.5 else (10 if peg_v <= 2.0 else 0)
        elif is_tech: return 10 if peg_v < 1.5 else (5 if peg_v <= 2.0 else 0)
        else: return 10 if peg_v < 1.0 else (5 if peg_v <= 1.5 else 0)

    def get_ps_pts(ps_val, rev_fwd_g):
        if ps_val is None or ps_val <= 0: return 0
        ebit_m = clean_percent(metrics.get("ebit_margin") or 0)
        ebitda_m = clean_percent(metrics.get("ebitda_margin") or 0)
        net_m = clean_percent(metrics.get("net_profit_margin") or 0)
        margin = net_m if net_m > 0 else (ebit_m if ebit_m > 0 else ebitda_m)
        
        target_pe_mapping = {
            "Technology": 25, "Software": 30, "Semiconductors": 25,
            "Healthcare": 20, "Consumer Defensive": 20, "Financial Services": 15,
            "Energy": 12, "Utilities": 15, "Real Estate": 18,
            "Industrials": 18, "Basic Materials": 15, "Communication Services": 20,
            "Consumer Cyclical": 18
        }
        sector_str = str(metrics.get("sector") or "")
        target_pe = target_pe_mapping.get(sector_str, 18)
        target_ps = target_pe * (margin / 100.0) if margin > 0 else 1.5
        
        if margin > 20:
            return 10 if ps_val <= target_ps else (5 if ps_val <= target_ps * 1.5 else 0)
        elif margin > 0:
            return 10 if ps_val <= target_ps else (5 if ps_val <= target_ps * 1.5 else 0)
        elif margin < 0:
            return 5 if rev_fwd_g and rev_fwd_g > 20 and ps_val <= 5.0 else 0
        return 0
"""

content = content.replace("        # 5. Standard Sector Buy Score Routing", helpers + "\n        # 5. Standard Sector Buy Score Routing")

content = re.sub(r'get_monopoly_pe_pts\(pe,\s*hist_pe,\s*\d+\)\s*if\s*is_monopoly\s*else\s*get_rel_pts\(pe,\s*sec_pe,\s*hist_pe,\s*\d+\)', r'get_pe_pts(pe, eps_2y_g, rev_2y_g)', content)
content = re.sub(r'get_rel_pts\(pb,\s*sec_pb,\s*hist_pb,\s*\d+\)', r'get_pb_pts(pb)', content)
content = re.sub(r'get_rel_pts\(ev_ebitda,\s*sec_ev_ebitda,\s*hist_ev,\s*\d+\)', r'get_ev_ebitda_pts(ev_ebitda, pe, eps_2y_g, rev_2y_g)', content)
content = re.sub(r'get_rel_pts\(peg_val,\s*sec_peg,\s*None,\s*\d+\)', r'get_peg_pts(peg_val, pe, eps_2y_g)', content)
content = re.sub(r'get_rel_pts\(ps,\s*sec_ps,\s*hist_ps,\s*\d+\)', r'get_ps_pts(ps, rev_2y_g)', content)

content = re.sub(r'get_rel_pts\(p_affo,\s*sec_pe,\s*hist_pe,\s*\d+\)', r'(20 if p_affo <= 15 else (10 if p_affo <= 18 else 0))', content)
content = re.sub(r'get_rel_pts\(p_ocf,\s*sec_pe,\s*hist_pe,\s*\d+\)', r'(20 if p_ocf <= 15 else (10 if p_ocf <= 18 else 0))', content)

with open("models/scoring.py", "w", encoding="utf-8") as f:
    f.write(content)
