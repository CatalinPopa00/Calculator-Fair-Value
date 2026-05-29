import sys

def main():
    file_path = 'c:/Users/Snoozie/Downloads/Calculator-Fair-Value/Calculator-Fair-Value/app.js'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    old_rel = """            const company_fcf_share = (rel.company_fcf_share || 0);
            const company_book_share = rel.company_book_share || 0; // Book value remains TTM
            const company_ebitda = (globalData.ebitda || 0);
            const company_debt = globalData.total_debt || 0;
            const company_cash = globalData.total_cash || 0;

            const variantEl = document.getElementById('relative-variant');
            const variant = variantEl ? variantEl.value : 'peers';"""

    new_rel = """            const dynEpsG = window._getDynamicEpsGrowth ? window._getDynamicEpsGrowth() : (prof.earnings_growth || 0);
            const dynRevG = window._getDynamicRevGrowth ? window._getDynamicRevGrowth() : (prof.revenue_growth || 0);
            
            const company_fcf_share = (rel.company_fcf_share || 0) * (1 + dynEpsG);
            const company_book_share = rel.company_book_share || 0; // Book value remains TTM
            const company_ebitda = (globalData.ebitda || 0) * (1 + dynEpsG);
            const company_debt = globalData.total_debt || 0;
            const company_cash = globalData.total_cash || 0;

            const variantEl = document.getElementById('relative-variant');
            const variant = variantEl ? variantEl.value : 'peers';"""

    old_fvPS = """            fvPE = company_eps * bPE;
            fvPFCF = company_fcf_share * bPFCF;
            let rev = (globalData.revenue || 0);
            if (globalData.company_profile && globalData.company_profile.revenue_growth) {
                rev = rev * (1 + globalData.company_profile.revenue_growth);
            }
            const ev_sales = rev * bPS;
            fvPS = company_shares > 0 ? (ev_sales - company_debt + company_cash) / company_shares : 0;
            fvPB = company_book_share * bPB;"""
            
    new_fvPS = """            fvPE = company_eps * bPE;
            fvPFCF = company_fcf_share * bPFCF;
            let rev = company_sales_share * company_shares;
            if (!rev || rev === 0) {
                rev = (globalData.revenue || 0) * (1 + dynRevG);
            }
            const ev_sales = rev * bPS;
            fvPS = company_shares > 0 ? (ev_sales - company_debt + company_cash) / company_shares : 0;
            fvPB = company_book_share * bPB;"""

    if old_rel in content and old_fvPS in content:
        content = content.replace(old_rel, new_rel)
        content = content.replace(old_fvPS, new_fvPS)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Success")
    else:
        print("Failed to find targets")

if __name__ == '__main__':
    main()
