"""Test what get_yahoo_analysis_normalized returns for TSM"""
import sys, os
sys.path.insert(0, os.getcwd())
from scraper.yahoo import get_yahoo_analysis_normalized
import json

result = get_yahoo_analysis_normalized("TSM")
print(json.dumps(result, indent=2, default=str))
