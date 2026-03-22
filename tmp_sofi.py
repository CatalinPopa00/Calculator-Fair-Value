import sys
from dotenv import load_load
import finnhub
import os
import requests

def test_sofi():
    print("Testing Finnhub vs Yahoo for SOFI")
    try:
        fh = finnhub.Client(api_key=os.environ.get('FINNHUB_API_KEY'))
        print("Finnhub Peers:", fh.company_peers('SOFI'))
    except Exception as e:
        print("Finnhub Failed:", e)

    url = "https://query2.finance.yahoo.com/v6/finance/recommendationsbysymbol/SOFI"
    resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    rec = resp.json().get('finance', {}).get('result', [])
    if rec:
        peers = [r.get('symbol') for r in rec[0].get('recommendedSymbols', [])]
        print("Yahoo Peers:", peers)

test_sofi()
