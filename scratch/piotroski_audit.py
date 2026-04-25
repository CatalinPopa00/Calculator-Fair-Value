
import yfinance as yf
import pandas as pd
import json

def calculate_piotroski(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    
    # Fetch financials
    income_stmt = ticker.financials
    balance_sheet = ticker.balance_sheet
    cash_flow = ticker.cashflow
    
    if income_stmt.empty or balance_sheet.empty or cash_flow.empty:
        return "Missing data for " + ticker_symbol

    # Get last 2 fiscal years
    cols = income_stmt.columns[:2]
    cy = cols[0] # Current Year
    py = cols[1] # Previous Year

    # 1. Extraction of Raw Data
    def get_val(df, label, col):
        if label in df.index:
            val = df.loc[label, col]
            return float(val) if not pd.isna(val) else 0
        return 0

    net_income_cy = get_val(income_stmt, 'Net Income', cy)
    net_income_py = get_val(income_stmt, 'Net Income', py)
    
    total_assets_cy = get_val(balance_sheet, 'Total Assets', cy)
    total_assets_py = get_val(balance_sheet, 'Total Assets', py)
    total_assets_py2 = get_val(balance_sheet, 'Total Assets', balance_sheet.columns[2]) if len(balance_sheet.columns) > 2 else total_assets_py

    cfo_cy = get_val(cash_flow, 'Operating Cash Flow', cy)
    cfo_py = get_val(cash_flow, 'Operating Cash Flow', py)
    
    capex_cy = abs(get_val(cash_flow, 'Capital Expenditure', cy))
    capex_py = abs(get_val(cash_flow, 'Capital Expenditure', py))
    fcf_cy = cfo_cy - capex_cy
    fcf_py = cfo_py - capex_py

    total_debt_cy = get_val(balance_sheet, 'Total Debt', cy)
    total_debt_py = get_val(balance_sheet, 'Total Debt', py)

    current_assets_cy = get_val(balance_sheet, 'Current Assets', cy)
    current_assets_py = get_val(balance_sheet, 'Current Assets', py)
    current_liab_cy = get_val(balance_sheet, 'Current Liabilities', cy) # Corrected label
    current_liab_py = get_val(balance_sheet, 'Current Liabilities', py) # Corrected label
    
    shares_cy = get_val(balance_sheet, 'Ordinary Shares Number', cy)
    shares_py = get_val(balance_sheet, 'Ordinary Shares Number', py)

    revenue_cy = get_val(income_stmt, 'Total Revenue', cy)
    revenue_py = get_val(income_stmt, 'Total Revenue', py)
    
    gross_profit_cy = get_val(income_stmt, 'Gross Profit', cy)
    gross_profit_py = get_val(income_stmt, 'Gross Profit', py)

    # 2. Piotroski F-Score Calculation
    f_score = 0
    details = []

    # Profitability
    roa_cy = net_income_cy / total_assets_py if total_assets_py > 0 else 0
    c1 = 1 if roa_cy > 0 else 0
    f_score += c1
    details.append(f"1. ROA Positiv ({roa_cy*100:.2f}%): {c1}")

    c2 = 1 if cfo_cy > 0 else 0
    f_score += c2
    details.append(f"2. CFO Positiv (${cfo_cy/1e9:.2f}B): {c2}")

    roa_py = net_income_py / total_assets_py2 if total_assets_py2 > 0 else 0
    c3 = 1 if roa_cy > roa_py else 0
    f_score += c3
    details.append(f"3. Îmbunătățire ROA ({roa_cy*100:.2f}% vs {roa_py*100:.2f}%): {c3}")

    c4 = 1 if cfo_cy > net_income_cy else 0
    f_score += c4
    details.append(f"4. Calitate Profit (CFO > NI): {c4}")

    # Leverage, Liquidity and Source of Funds
    lev_cy = total_debt_cy / total_assets_cy if total_assets_cy > 0 else 0
    lev_py = total_debt_py / total_assets_py if total_assets_py > 0 else 0
    c5 = 1 if lev_cy < lev_py else 0
    f_score += c5
    details.append(f"5. Scădere Leverage ({lev_cy:.3f} vs {lev_py:.3f}): {c5}")

    cr_cy = current_assets_cy / current_liab_cy if current_liab_cy > 0 else 0
    cr_py = current_assets_py / current_liab_py if current_liab_py > 0 else 0
    c6 = 1 if cr_cy > cr_py else 0
    f_score += c6
    details.append(f"6. Îmbunătățire Lichiditate ({cr_cy:.2f} vs {cr_py:.2f}): {c6}")

    c7 = 1 if shares_cy <= shares_py else 0
    f_score += c7
    details.append(f"7. Fără Diluare ({shares_cy/1e6:.1f}M vs {shares_py/1e6:.1f}M): {c7}")

    # Operating Efficiency
    gm_cy = gross_profit_cy / revenue_cy if revenue_cy > 0 else 0
    gm_py = gross_profit_py / revenue_py if revenue_py > 0 else 0
    c8 = 1 if gm_cy > gm_py else 0
    f_score += c8
    details.append(f"8. Îmbunătățire Marjă Brută ({gm_cy*100:.2f}% vs {gm_py*100:.2f}%): {c8}")

    at_cy = revenue_cy / total_assets_py if total_assets_py > 0 else 0
    at_py = revenue_py / total_assets_py2 if total_assets_py2 > 0 else 0
    c9 = 1 if at_cy > at_py else 0
    f_score += c9
    details.append(f"9. Îmbunătățire Asset Turnover ({at_cy:.3f} vs {at_py:.3f}): {c9}")

    # 3. Rule of 40
    rev_growth = (revenue_cy - revenue_py) / revenue_py if revenue_py > 0 else 0
    fcf_margin = fcf_cy / revenue_cy if revenue_cy > 0 else 0
    rule_of_40 = (rev_growth + fcf_margin) * 100

    return {
        "ticker": ticker_symbol,
        "years": [str(cy.year), str(py.year)],
        "raw_data": {
            "cfo": [cfo_cy, cfo_py],
            "fcf": [fcf_cy, fcf_py],
            "shares": [shares_cy, shares_py],
            "net_income": [net_income_cy, net_income_py],
            "total_debt": [total_debt_cy, total_debt_py],
            "revenue": [revenue_cy, revenue_py],
            "total_assets": [total_assets_cy, total_assets_py]
        },
        "f_score": f_score,
        "f_details": details,
        "rule_of_40": {
            "growth": rev_growth,
            "fcf_margin": fcf_margin,
            "sum": rule_of_40
        }
    }

res = calculate_piotroski("UBER")
print(json.dumps(res, indent=2))
