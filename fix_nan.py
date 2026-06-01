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

    with open('app.js', 'w', encoding='utf-8') as f:
        f.write(app_js)

def update_scoring_py():
    with open('models/scoring.py', 'r', encoding='utf-8') as f:
        scoring_py = f.read()
    
    # Update calculate_rule_of_40
    # First, find calculate_rule_of_40 block
    start_pattern = r"def calculate_rule_of_40\(metrics\):.*?(?=\n\n|\Z)"
    match = re.search(start_pattern, scoring_py, re.DOTALL)
    
    if match:
        old_block = match.group(0)
        
        # Rewrite the block manually to inject the fwd revenue logic
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
        "total": total,
        "passed": total >= 40.0,
        "rev_growth_label": rev_growth_label,
        "rev_growth_desc": rev_growth_desc,
        "breakdown": [
            {
                "metric": rev_growth_label,
                "value": f"{rev_growth:.1f}%",
                "desc": rev_growth_desc
            },
            {
                "metric": "FCF Margin",
                "value": f"{fcf_margin:.1f}%",
                "desc": "Free Cash Flow relative to Total Revenue."
            }
        ]
    }"""
        scoring_py = scoring_py.replace(old_block, new_block)
        with open('models/scoring.py', 'w', encoding='utf-8') as f:
            f.write(scoring_py)

if __name__ == '__main__':
    update_app_js()
    update_scoring_py()
    print("Fixed app.js and models/scoring.py")
