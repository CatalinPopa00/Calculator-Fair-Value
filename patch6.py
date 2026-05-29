import sys
import re

def main():
    file_path = 'c:/Users/Snoozie/Downloads/Calculator-Fair-Value/Calculator-Fair-Value/app.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    pattern = r"let val = null;\s+if \(k === 'PE' \|\| k === 'P_FFO'\) \{\s+val = globalData\.company_profile && \(globalData\.company_profile\.fwd_pe \|\| globalData\.company_profile\.forward_pe\);\s+\}\s+else if \(k === 'PS'\) \{\s+val = globalData\.company_profile && \(globalData\.company_profile\.fwd_ps \|\| globalData\.company_profile\.forward_ev_sales\);\s+\}\s+else if \(k === 'PB'\) val = globalData\.company_profile && globalData\.company_profile\.price_to_book;\s+else if \(k === 'PFCF'\) \{\s+let mainPfcf = null;\s+if \(globalData\.company_profile && globalData\.company_profile\.pfcf_ratio\) mainPfcf = globalData\.company_profile\.pfcf_ratio;\s+else if \(globalData\.market_cap && r\.company_fcf_share && r\.company_fcf_share > 0\) mainPfcf = globalData\.market_cap \/ \(r\.company_fcf_share \* \(globalData\.company_profile\.shares_outstanding \|\| 1\)\);\s+val = mainPfcf;\s+\}\s+else if \(k === 'EV_EBITDA'\) \{\s+if \(globalData\.company_profile && globalData\.company_profile\.forward_ev_ebitda\) val = globalData\.company_profile\.forward_ev_ebitda;\s+else if \(globalData\.ebitda && globalData\.ebitda > 0\) val = \(globalData\.market_cap \+ \(globalData\.total_debt \|\| 0\) - \(globalData\.total_cash \|\| 0\)\) \/ globalData\.ebitda;\s+\}"

    new_target = """let val = null;
                                    const impliedPe = r.dynamic_company_eps > 0 ? (_realApiPrice / r.dynamic_company_eps) : (globalData.company_profile && (globalData.company_profile.fwd_pe || globalData.company_profile.forward_pe));
                                    
                                    const dynEpsG = window._getDynamicEpsGrowth ? window._getDynamicEpsGrowth() : (globalData.company_profile?.earnings_growth || 0);
                                    const dynEbitda = (globalData.ebitda || 0) * (1 + dynEpsG);
                                    const impliedEvEbitda = dynEbitda > 0 ? (globalData.market_cap + (globalData.total_debt || 0) - (globalData.total_cash || 0)) / dynEbitda : null;
                                    
                                    const dynRevG = window._getDynamicRevGrowth ? window._getDynamicRevGrowth() : (globalData.company_profile?.revenue_growth || 0);
                                    const rev = r.dynamic_company_sales_share ? r.dynamic_company_sales_share * (globalData.company_profile?.shares_outstanding || 1) : ((globalData.revenue || 0) * (1 + dynRevG));
                                    const impliedPs = rev > 0 ? (globalData.market_cap + (globalData.total_debt || 0) - (globalData.total_cash || 0)) / rev : null;
                                    
                                    if (k === 'PE' || k === 'P_FFO') {
                                        val = impliedPe;
                                    }
                                    else if (k === 'PS') {
                                        val = impliedPs || (globalData.company_profile && (globalData.company_profile.fwd_ps || globalData.company_profile.forward_ev_sales));
                                    }
                                    else if (k === 'PB') val = globalData.company_profile && globalData.company_profile.price_to_book;
                                    else if (k === 'PFCF') {
                                        const dynFcfShare = (r.company_fcf_share || 0) * (1 + dynEpsG);
                                        val = dynFcfShare > 0 ? _realApiPrice / dynFcfShare : null;
                                    }
                                    else if (k === 'EV_EBITDA') {
                                        val = impliedEvEbitda || (globalData.company_profile && globalData.company_profile.forward_ev_ebitda);
                                    }"""

    if re.search(pattern, content):
        content = re.sub(pattern, new_target, content)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Success")
    else:
        print("Failed to find targets")

if __name__ == '__main__':
    main()
