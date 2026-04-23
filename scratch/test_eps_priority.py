
import datetime

# Mock data
raw_data_map = {"2025": {}}

def add_to_map(dt_obj, eps_val, priority=1):
    yr_key = str(dt_obj.year)
    if yr_key not in raw_data_map: raw_data_map[yr_key] = {}
    
    dt_key = dt_obj.strftime('%Y-%m-%d')
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
        raw_data_map[yr_key][dt_key] = (float(eps_val), priority)

# Test UBER case
dt = datetime.datetime(2025, 11, 4)

print("Adding Calendar (P1) val 3.11...")
add_to_map(dt, 3.11, priority=1)
print(f"Map: {raw_data_map['2025']}")

print("\nAdding Nasdaq (P3) val 0.70...")
add_to_map(dt, 0.70, priority=3)
print(f"Map: {raw_data_map['2025']}")

print("\nAdding History (P2) val 0.75...")
add_to_map(dt, 0.75, priority=2)
print(f"Map: {raw_data_map['2025']}")
