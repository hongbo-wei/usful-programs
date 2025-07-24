
import yfinance as yf
from stock_trader.config import DB_PATH  # For future use if needed
from functools import lru_cache
import time

"""
数据相关工具函数。
"""

# Cache stock prices for 60 seconds to reduce API calls
@lru_cache(maxsize=64)
def _cached_stock_price(symbol, _ts):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='1d')
        if not data.empty:
            return round(data['Close'].iloc[-1], 2)
    except Exception:
        pass
    return None


def get_stock_price(symbol):
    """
    获取指定股票/加密货币的最新收盘价，缓存60秒。
    symbol: 股票或加密货币代码，如 'AAPL' 或 'BTC-USD'
    返回: float 或 None
    """
    # Use current minute as cache key, so cache is valid for 60 seconds
    ts = int(time.time() // 60)
    return _cached_stock_price(symbol, ts)
