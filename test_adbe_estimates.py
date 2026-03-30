import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.scraper.yahoo import get_analyst_data

for ticker in ['ADBE', 'SMCI']:
    print(f"\n{'='*60}")
    print(f"  {ticker}")
    print(f"{'='*60}")
    data = get_analyst_data(ticker)

    print("  EPS ESTIMATES:")
    for e in data.get('eps_estimates', []):
        period = e.get('period', '?')
        status = e.get('status', '?')
        growth = e.get('growth')
        surprise = e.get('surprise_pct')
        rc = e.get('reported_count', '-')
        g = f"{growth*100:.1f}%" if growth is not None else "None"
        s = f"{surprise*100:.1f}%" if surprise is not None else "None"
        print(f"    {period} [{status}] growth={g} surp={s} rc={rc}")

    print("  REVENUE ESTIMATES:")
    for r in data.get('rev_estimates', []):
        period = r.get('period', '?')
        status = r.get('status', '?')
        growth = r.get('growth')
        surprise = r.get('surprise_pct')
        rc = r.get('reported_count', '-')
        g = f"{growth*100:.1f}%" if growth is not None else "None"
        s = f"{surprise*100:.1f}%" if surprise is not None else "None"
        print(f"    {period} [{status}] growth={g} surp={s} rc={rc}")
