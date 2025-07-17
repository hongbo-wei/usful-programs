import yfinance as yf

def get_stock_price(symbol):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period='1d')
    if not data.empty:
        return round(data['Close'].iloc[-1], 2)
    return None
