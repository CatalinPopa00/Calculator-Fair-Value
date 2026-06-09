with open('api/index.py', 'r') as f:
    content = f.read()

target = """        if not price:
            info = stock.info
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            currency = info.get("currency", "USD")

        # Ensure we always return the USD equivalent to match the platform's standard
        price_fx = get_usd_fx_rate(currency)
        if price and price_fx != 1.0:
            price = price * price_fx

        return {"ticker": ticker, "price": price, "currency": "USD"}"""

replacement = """        info = stock.info
        if not price:
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")

        currency = info.get("currency", "USD")
        open_price = info.get("regularMarketOpen") or info.get("open") or info.get("previousClose")

        # Ensure we always return the USD equivalent to match the platform's standard
        price_fx = get_usd_fx_rate(currency)
        if price and price_fx != 1.0:
            price = price * price_fx
        if open_price and price_fx != 1.0:
            open_price = open_price * price_fx

        return {"ticker": ticker, "price": price, "open_price": open_price, "currency": "USD"}"""

content = content.replace(target, replacement)

with open('api/index.py', 'w') as f:
    f.write(content)
