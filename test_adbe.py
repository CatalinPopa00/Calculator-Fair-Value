from scraper.yahoo import get_company_data
import json
data = get_company_data('ADBE')
hist = data['historical_trends']
for h in hist:
    print(f"{h['year']}: Rev {h['revenue']/1e9:.2f} B, EPS {h['eps']:.2f}, NI margin {h['net_margin']*100:.2f}%, GAAP margin {h['gaap_net_margin']*100:.2f}%")
