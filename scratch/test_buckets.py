
import re
import datetime

def test_buckets():
    this_q = 2 # Current Q
    target_fy = 2026 # Current FY
    
    eps_estimates = [
        {"period_code": "0q", "avg": 4.60},
        {"period_code": "+1q", "avg": 5.00},
        {"period_code": "+2q", "avg": 5.50},
        {"period_code": "+3q", "avg": 6.00},
        {"period_code": "+4q", "avg": 6.50},
    ]
    
    eps_buckets = {f"Q{i}": {"avg": None} for i in range(1, 5)}
    eps_buckets.update({"FY0": {"avg": None}, "FY1": {"avg": None}})
    
    def fill_buckets(buckets, source, target_fy, this_q):
        for item in source:
            code = str(item.get('period_code', ''))
            if 'q' in code:
                rel_idx = int(code.replace('q', '').replace('+', ''))
                total_q = this_q + rel_idx
                q_num = ((total_q - 1) % 4) + 1
                yr = target_fy + (total_q - 1) // 4
                
                if yr == target_fy:
                    idx = f"Q{q_num}"
                    buckets[idx]["avg"] = item["avg"]
                elif yr == target_fy + 1:
                    # Logic for next year's quarters could be added, but currently buckets only has current FY quarters
                    pass
                
                print(f"Code {code} -> Q{q_num} {yr}")

    fill_buckets(eps_buckets, eps_estimates, target_fy, this_q)
    print("Buckets:", eps_buckets)

if __name__ == "__main__":
    test_buckets()
