import re

with open('api/kpi_audit.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_inst_4 = "4. **Earnings & Revenue Estimates & CAGR:** If the user asks about EPS or Revenue estimates on multiple years, you MUST read the `Estimates` context block which contains exact EPS and Revenue estimates from Yahoo/Nasdaq for the next 2-3 years. List them explicitly, and ALWAYS automatically calculate the Compound Annual Growth Rate (CAGR) to show the growth trajectory. NEVER say you do not know the estimates without checking the `Estimates` context."

new_inst_4 = "4. **Earnings & Revenue Estimates & CAGR:** Our local `Estimates` context only has data for the next 2 years. If the user asks for multi-year estimates (e.g. 3, 4, or 5 years) from Nasdaq, YOU MUST ACTIVELY USE THE SEARCH TOOL to search 'Nasdaq [ticker] earnings estimates' to fetch the 4+ years of EPS and Revenue estimates directly from the web! Also, when calculating the Compound Annual Growth Rate (CAGR) for these estimates, you MUST ALWAYS calculate it starting from the LAST FULLY REPORTED YEAR (the most recently completed historical year), NOT starting from an estimated year like 2026."

if old_inst_4 in content:
    content = content.replace(old_inst_4, new_inst_4)
    with open('api/kpi_audit.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Replaced instruction 4 successfully.")
else:
    print("Instruction 4 not found.")
