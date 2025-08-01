import os

# Centralized configuration for the stock trader app
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get('STOCKTRADER_DB_PATH') or os.path.join(BASE_DIR, 'stock_trader', 'data', 'trades.db')


# Centralized constants
DEFAULT_INITIAL_FUND = 1_000_000_000  # Default initial fund for trading
