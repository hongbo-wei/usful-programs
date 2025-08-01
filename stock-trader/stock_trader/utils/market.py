from stock_trader.data import get_stock_price

def get_symbols():
    """Return the list of supported stock and crypto symbols."""
    return [
        "AAPL", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "BTC-USD", "ETH-USD"
    ]

def get_market_rows(symbols):
    """Return a list of dicts with symbol and current price."""
    return [{"Symbol": symbol, "Price": get_stock_price(symbol)} for symbol in symbols]

def get_asset_categories():
    """Return stock and crypto symbol categories as tuple."""
    stock_symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "TSLA"]
    crypto_symbols = ["BTC-USD", "ETH-USD"]
    return stock_symbols, crypto_symbols

def summarize_asset_values(position_rows):
    """Calculate buy and market values for stocks and cryptos."""
    stock_symbols, crypto_symbols = get_asset_categories()
    stock_buy = stock_market = crypto_buy = crypto_market = 0
    for row in position_rows:
        symbol = row["Symbol"]
        buy_cost = row["Buy Price"] * row["Quantity"]
        market_value = row["Market Value"]
        if symbol in stock_symbols:
            stock_buy += buy_cost
            stock_market += market_value
        elif symbol in crypto_symbols:
            crypto_buy += buy_cost
            crypto_market += market_value
    return stock_buy, stock_market, crypto_buy, crypto_market
