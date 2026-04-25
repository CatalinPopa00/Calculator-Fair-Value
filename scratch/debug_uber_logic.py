
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import scraper.yahoo as yahoo
import json
import datetime

ticker = "UBER"

# Mock log to see what happens
def mock_log(*args, **kwargs):
    print("LOG:", *args, **kwargs)

yahoo.log = mock_log

print(f"Testing Nasdaq surprise logic for {ticker}...")
nq_surprises = yahoo.get_nasdaq_earnings_surprise(ticker)

raw_data_map = {}
fy_end_month = 12

def add_to_map(dt_obj, eps_val, priority=1):
    try:
        adj_dt = dt_obj - datetime.timedelta(days=65)
        ey = adj_dt.year if adj_dt.month <= fy_end_month else adj_dt.year + 1
        yr_key = str(ey)
        if yr_key not in raw_data_map: raw_data_map[yr_key] = {}
        found_duplicate = False
        for existing_dt_str in list(raw_data_map[yr_key].keys()):
            existing_dt = datetime.datetime.strptime(existing_dt_str, '%Y-%m-%d')
            if abs((dt_obj - existing_dt).days) <= 45:
                existing_val, existing_prio = raw_data_map[yr_key][existing_dt_str]
                if priority > existing_prio:
                    raw_data_map[yr_key][existing_dt_str] = (float(eps_val), priority)
                elif priority == existing_prio:
                    if abs(eps_val) > abs(existing_val):
                        raw_data_map[yr_key][existing_dt_str] = (float(eps_val), priority)
                found_duplicate = True
                break
        if not found_duplicate:
            dt_key = dt_obj.strftime('%Y-%m-%d')
            raw_data_map[yr_key][dt_key] = (float(eps_val), priority)
    except Exception as e:
        print(f"Error in add_to_map: {e}")

for row in nq_surprises:
    eps_val = row.get('eps')
    fc_val = row.get('consensusForecast')
    dt_str = row.get('dateReported')
    if eps_val is not None and dt_str:
        dt = datetime.datetime.strptime(dt_str, '%m/%d/%Y')
        final_eps = float(eps_val)
        try:
            if fc_val and float(fc_val) != 0:
                f_fc = float(fc_val)
                diff = abs(final_eps - f_fc)
                if (diff / abs(f_fc) > 0.25) or diff > 0.15:
                    print(f"NEUTRALIZING: {ticker} {dt_str} {final_eps} -> {f_fc}")
                    final_eps = f_fc
        except Exception as e:
            print(f"Error neutralizing: {e}")
        add_to_map(dt, final_eps, priority=3)

print("\n--- RAW DATA MAP ---")
print(json.dumps(raw_data_map, indent=2))

# Consolidation logic
adjusted_history = {}
for ey, quarters_dict in raw_data_map.items():
    vals = [v[0] for v in quarters_dict.values() if v is not None]
    if not vals: continue
    
    # Systemic Outlier Scrubbing
    if len(vals) >= 3:
        try:
            sorted_vals = sorted(vals)
            med = sorted_vals[len(vals)//2]
            if abs(med) > 0.05:
                refined_vals = []
                for v in vals:
                    if abs(v) > abs(med) * 3.0:
                        print(f"SCRUBBING OUTLIER: {ticker} in {ey} ({v} -> {med})")
                        refined_vals.append(med)
                    else:
                        refined_vals.append(v)
                vals = refined_vals
        except Exception as e:
            print(f"Error scrubbing: {e}")

    count = len(vals)
    total = sum(vals)
    if count >= 4:
        adjusted_history[ey] = total
    else:
        adjusted_history[ey] = (total / count) * 4.0

print("\n--- ADJUSTED HISTORY ---")
print(json.dumps(adjusted_history, indent=2))
