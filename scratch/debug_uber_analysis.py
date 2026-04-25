
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from scraper.yahoo import get_yahoo_analysis_normalized
import json

ticker = "UBER"
data = get_yahoo_analysis_normalized(ticker)

print(json.dumps(data, indent=2))
