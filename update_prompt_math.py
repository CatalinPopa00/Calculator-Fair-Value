import io
with io.open('api/kpi_audit.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '''VALUE EXTRACTION (5-YEAR HISTORY + RECENT QUARTERS):
For each identified KPI, search deeply and track their evolution over time over the last 5 full fiscal years (e.g., FY 2021, FY 2022, FY 2023, FY 2024, FY 2025).
ADDITIONALLY, for the CURRENT unfinished fiscal year, extract the available individual quarterly data (e.g., FY 2026 Q1, FY 2026 Q2). Do NOT use estimates.
Format the keys EXACTLY as "FY [Year]" or "FY [Year] Q[X]". Ensure exact numbers are extracted if explicitly stated. Format numbers cleanly (e.g. "1.2 Billion", "34.5%", "450 Million").'''

replace = '''VALUE EXTRACTION (5-YEAR HISTORY + RECENT QUARTERS):
For each identified KPI, track their evolution over the last 5 full fiscal years (e.g., FY 2021, FY 2022, FY 2023, FY 2024, FY 2025).
ADDITIONALLY, for the CURRENT unfinished fiscal year, extract the available individual quarterly data (e.g., FY 2026 Q1, FY 2026 Q2).
CRITICAL MATH RULE FOR QUARTERLY DATA: You are plotting Quarterly data on the same chart as Annual data! If the KPI is a cumulative "flow" metric (like Revenue, Gross Bookings, Volume), a single quarter will naturally look 4x smaller than a full year! To prevent this visual collapse, YOU MUST ANNUALIZE any quarterly flow metrics (multiply the quarter by 4, or use Trailing Twelve Months / TTM) so they are perfectly comparable to the Annual bars. If the KPI is a snapshot/point-in-time metric (like ARR, MAU, Subscribers, RPO), leave it exactly as is.
Format the keys EXACTLY as "FY [Year]" or "FY [Year] Q[X]". Format numbers cleanly (e.g. "1.2 Billion", "34.5%").'''

text = text.replace(target, replace)

with io.open('api/kpi_audit.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("Updated prompt for annualized data")
