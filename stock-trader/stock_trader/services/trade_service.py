from stock_trader.models.trade import Trade
from typing import List
import sqlite3
from datetime import datetime
from stock_trader.config import DB_PATH

DB_NAME = DB_PATH

import logging


# NOTE: For CSRF protection, ensure Flask-WTF is installed and configured in your Flask app (see app.py):
#   pip install Flask-WTF
#   from flask_wtf import CSRFProtect
#   csrf = CSRFProtect(app)
#   And add {{ csrf_token() }} in your HTML forms.

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

def init_db() -> None:
    """
    Initialize the trades database table if it does not exist.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                type TEXT,
                quantity INTEGER,
                price REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )''')
            conn.commit()
    except Exception as e:
        logger.exception("[DB] Failed to initialize database: %s", e)

def record_trade(symbol: str, trade_type: str, quantity: int, price: float) -> None:
    """
    Record a trade in the database.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO trades (symbol, type, quantity, price) VALUES (?, ?, ?, ?)', (symbol, trade_type, quantity, price))
            conn.commit()
    except Exception as e:
        logger.error("[DB] Failed to record trade: symbol=%s, type=%s, quantity=%s, price=%s, error=%s", symbol, trade_type, quantity, price, e)

def get_trades() -> List[Trade]:
    """
    Fetch all trades from the database, ordered by timestamp descending.
    Returns an empty list if an error occurs.
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            c = conn.cursor()
            c.execute('SELECT id, symbol, type, quantity, price, timestamp FROM trades ORDER BY timestamp DESC')
            rows = c.fetchall()
        trades = []
        for row in rows:
            id, symbol, type_, quantity, price, timestamp = row
            # Convert timestamp to datetime if it's a string
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp)
                except Exception as ex:
                    logger.warning("[DB] Failed to parse timestamp '%s': %s", timestamp, ex)
            trades.append(Trade(id, symbol, type_, quantity, price, timestamp))
        return trades
    except Exception as e:
        logger.error("[DB] Failed to fetch trades: %s", e)
        return []


from stock_trader.config import DB_PATH, DEFAULT_INITIAL_FUND

def calculate_positions_and_pnl(trades: list, initial_fund: float = DEFAULT_INITIAL_FUND):
    """
    Calculate positions, P&L, and related metrics.
    Args:
        trades (list[Trade]): List of trade records.
        initial_fund (float): Initial fund amount.
    Returns:
        tuple: (position_rows, cash_balance, position_value, total_asset_value, pnl, roi_str)
    """
    from collections import defaultdict
    from stock_trader.data import get_stock_price
    total_buy_cost = 0.0
    total_sell_income = 0.0
    positions = {}
    for t in trades:
        if t.type == 'Buy':
            positions.setdefault(t.symbol, []).append(t)
            total_buy_cost += t.quantity * t.price
        elif t.type == 'Sell':
            total_sell_income += t.quantity * t.price
    position_value = 0.0
    position_rows = []
    merged = defaultdict(lambda: {"total_qty":0, "total_cost":0.0, "first_date":None})
    for symbol, trade_list in positions.items():
        for trade in trade_list:
            merged[symbol]["total_qty"] += trade.quantity
            merged[symbol]["total_cost"] += trade.quantity * trade.price
            if merged[symbol]["first_date"] is None or trade.timestamp < merged[symbol]["first_date"]:
                merged[symbol]["first_date"] = trade.timestamp
    for symbol, data in merged.items():
        qty = data["total_qty"]
        avg_price = data["total_cost"] / qty if qty else 0.0
        buy_date = data["first_date"]
        try:
            if isinstance(buy_date, str):
                buy_date = datetime.fromisoformat(buy_date)
            buy_date_str = buy_date.strftime('%Y-%m-%d')
        except Exception as ex:
            logger.warning("[P&L] Failed to format buy_date '%s': %s", buy_date, ex)
            buy_date_str = str(buy_date)
        current_price = get_stock_price(symbol)
        if current_price is None:
            logger.warning("[Market] Failed to get current price for symbol '%s'", symbol)
            current_price = 0.0
        market_value = qty * current_price
        position_value += market_value
        position_rows.append({
            "Symbol": symbol,
            "Buy Date": buy_date_str,
            "Buy Price": round(avg_price, 2),
            "Current Price": current_price,
            "Quantity": qty,
            "Market Value": market_value,
            "P&L": market_value - data["total_cost"]
        })
    cash_balance = initial_fund - total_buy_cost + total_sell_income
    total_asset_value = cash_balance + position_value
    if not trades:
        cash_balance = initial_fund
        position_value = 0.0
        total_asset_value = initial_fund
    pnl = total_asset_value - initial_fund
    roi = (pnl / initial_fund) * 100 if initial_fund else 0.0
    roi_str = f"{roi:.4f}%"
    return position_rows, cash_balance, position_value, total_asset_value, pnl, roi_str

def execute_trade(symbol: str, trade_type: str, quantity: int, price: float = None) -> None:
    """
    执行一笔模拟交易，自动补充当前价格（如未指定），并写入数据库。
    """
    if price is None:
        # 这里可集成实时价格获取逻辑
        from stock_trader.data import get_stock_price
        price = get_stock_price(symbol)
    record_trade(symbol, trade_type, quantity, price)