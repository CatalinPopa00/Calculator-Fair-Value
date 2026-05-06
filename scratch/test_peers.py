
from yfinance.screener.screener import screen as yf_screen
from yfinance.screener.query import EquityQuery
import yfinance as yf

def test_peers(ticker):
    inf = yf.Ticker(ticker).info
    ind = inf.get('industry','')
    s_ind = ind.replace(' - ', '\u2014')
    q_ind = EquityQuery('eq', ['industry', s_ind])
    q_ex1 = EquityQuery('eq', ['exchange', 'NMS'])
    q_ex2 = EquityQuery('eq', ['exchange', 'NYQ'])
    q_us = EquityQuery('or', [q_ex1, q_ex2])
    q = EquityQuery('and', [q_ind, q_us])
    res = yf_screen(q, size=15, sortField='intradaymarketcap', sortAsc=False)
    print(f"\n{ticker} ({ind}) PEERS:")
    for qt in res.get('quotes', [])[:10]:
        if qt.get('symbol') != ticker:
            print(f"  - {qt.get('symbol')} ({qt.get('shortName')})")

test_peers('ADBE')
test_peers('PLTR')
test_peers('SOFI')
test_peers('FDS')
