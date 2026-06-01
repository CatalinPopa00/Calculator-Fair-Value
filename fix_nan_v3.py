import re

def update_app_js():
    with open('app.js', 'r', encoding='utf-8') as f:
        app_js = f.read()

    # Fix NaN issue by providing points_awarded
    app_js = app_js.replace(
        'points: r40Pts, max_points: 30, display_type: "raw"',
        'points: r40Pts, points_awarded: r40Pts, max_points: 30, display_type: "raw"'
    )
    app_js = app_js.replace(
        'points: evGpPts, max_points: 25, display_type: "raw"',
        'points: evGpPts, points_awarded: evGpPts, max_points: 25, display_type: "raw"'
    )
    app_js = app_js.replace(
        'points: gmTrendPts, max_points: 25, display_type: "raw"',
        'points: gmTrendPts, points_awarded: gmTrendPts, max_points: 25, display_type: "raw"'
    )
    app_js = app_js.replace(
        'points: qrPts, max_points: 20, display_type: "raw"',
        'points: qrPts, points_awarded: qrPts, max_points: 20, display_type: "raw"'
    )

    # Use Fwd 1Y Revenue Growth for Rule of 40 in app.js
    old_r40_logic = """const ebitdaMargin = (data.company_profile.ebitda_margins || 0) * (data.company_profile.ebitda_margins > 1 ? 1 : 100);
                const ruleOf40 = rev_growth + ebitdaMargin;"""
    
    new_r40_logic = """const ebitdaMargin = (data.company_profile.ebitda_margins || 0) * (data.company_profile.ebitda_margins > 1 ? 1 : 100);
                const ttmRev = data.company_profile.total_revenue || 0;
                const fwdRev1Y = data.company_profile.forward_revenue || 0;
                let rev_growth_for_r40 = rev_growth;
                if (ttmRev > 0 && fwdRev1Y > 0) {
                    rev_growth_for_r40 = ((fwdRev1Y / ttmRev) - 1) * 100;
                }
                const ruleOf40 = rev_growth_for_r40 + ebitdaMargin;"""
    app_js = app_js.replace(old_r40_logic, new_r40_logic)

    # Patch the renderRule40Breakdown in app.js
    old_render = """<div style="font-size:0.85rem; font-weight:700; color:white;">Revenue Growth</div>
                        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">Most recent historical 1-year revenue growth.</div>"""
    new_render = """<div style="font-size:0.85rem; font-weight:700; color:white;">${rule40Data.rev_growth_label || 'Revenue Growth'}</div>
                        <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">${rule40Data.rev_growth_desc || 'Most recent historical 1-year revenue growth.'}</div>"""
    app_js = app_js.replace(old_render, new_render)

    with open('app.js', 'w', encoding='utf-8') as f:
        f.write(app_js)

def update_scoring_py():
    with open('models/scoring.py', 'r', encoding='utf-8') as f:
        scoring_py = f.read()
    
    # We will replace the entire calculate_rule_of_40 block exactly
    start_pattern = r"def calculate_rule_of_40\(metrics\):.*?(?=\n\n# v268: Sync with clean_percent|\Z)"
    # Actually wait, let's just find the def calculate_rule_of_40 and replace until return { ... }
    
    match = re.search(r"def calculate_rule_of_40\(metrics\):.*?return \{\n.*?\n    \}", scoring_py, re.DOTALL)
    if match:
        old_block = match.group(0)
        new_block = """def calculate_rule_of_40(metrics):
    \"\"\"
    SaaS Rule of 40: Revenue Growth + FCF Margin >= 40%
    \"\"\"
    def safe_float(val, default=0.0):
        if val is None: return default
        try: return float(val)
        except: return default

    prof = metrics.get('company_profile', {})
    fwd_rev = safe_float(prof.get('forward_revenue'))
    ttm_rev = safe_float(prof.get('total_revenue') or metrics.get('revenue'))
    
    if fwd_rev > 0 and ttm_rev > 0:
        rev_growth_raw = (fwd_rev / ttm_rev) - 1.0
        rev_growth_label = "Fwd 1Y Revenue Growth"
        rev_growth_desc = "Estimates for the next 12 months."
    else:
        rev_growth_raw = safe_float(metrics.get('revenue_growth'))
        rev_growth_label = "Revenue Growth"
        rev_growth_desc = "Most recent historical 1-year revenue growth."

    rev_growth = rev_growth_raw * 100.0 if (0 < abs(rev_growth_raw) < 1.0) else rev_growth_raw
    
    fcf = safe_float(metrics.get('fcf'))
    rev = safe_float(metrics.get('revenue') or ttm_rev)
    fcf_margin = (fcf / rev * 100.0) if (fcf and rev and rev > 0) else 0.0
    
    total = rev_growth + fcf_margin
    
    return {
        "revenue_growth": round(rev_growth, 2),
        "fcf_margin": round(fcf_margin, 2),
        "total": round(total, 2),
        "passed": total >= 40,
        "label": "Strong" if total >= 40 else ("Healthy" if total >= 30 else "Weak"),
        "rev_growth_label": rev_growth_label,
        "rev_growth_desc": rev_growth_desc
    }"""
        scoring_py = scoring_py.replace(old_block, new_block)
        with open('models/scoring.py', 'w', encoding='utf-8') as f:
            f.write(scoring_py)

if __name__ == '__main__':
    update_app_js()
    update_scoring_py()
    print("Fixed app.js and models/scoring.py")
