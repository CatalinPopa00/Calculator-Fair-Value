from scraper.yahoo import get_company_synthesis
import yfinance as yf

ticker = 'ADBE'
stock = yf.Ticker(ticker)
info = stock.info

synthesis = get_company_synthesis(ticker, info, run_ai=True)
print(synthesis)
