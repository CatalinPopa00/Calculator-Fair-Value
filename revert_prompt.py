import io
with io.open('api/kpi_audit.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''CRITICAL MATH RULE FOR QUARTERLY DATA: You are plotting Quarterly data on the same chart as Annual data! If the KPI is a cumulative "flow" metric (like Revenue, Gross Bookings, Volume), a single quarter will naturally look 4x smaller than a full year! To prevent this visual collapse, YOU MUST ANNUALIZE any quarterly flow metrics (multiply the quarter by 4, or use Trailing Twelve Months / TTM) so they are perfectly comparable to the Annual bars. If the KPI is a snapshot/point-in-time metric (like ARR, MAU, Subscribers, RPO), leave it exactly as is.
Format the keys EXACTLY as "FY [Year]" or "FY [Year] Q[X]". Format numbers cleanly (e.g. "1.2 Billion", "34.5%").'''

replace = '''Format the keys EXACTLY as "FY [Year]" or "FY [Year] Q[X]". Ensure exact numbers are extracted if explicitly stated. Format numbers cleanly (e.g. "1.2 Billion", "34.5%", "450 Million").'''

text = text.replace(target, replace)

with io.open('api/kpi_audit.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Reverted math rule")
