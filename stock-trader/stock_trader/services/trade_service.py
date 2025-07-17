from stock_trader.models.trade import Trade
from typing import List
import sqlite3
from datetime import datetime

DB_NAME = 'stock_trader/data/trades.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
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
    conn.close()

def record_trade(symbol: str, trade_type: str, quantity: int, price: float):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO trades (symbol, type, quantity, price) VALUES (?, ?, ?, ?)', (symbol, trade_type, quantity, price))
    conn.commit()
    conn.close()

def get_trades() -> List[Trade]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT id, symbol, type, quantity, price, timestamp FROM trades ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()
    return [Trade(*row) for row in rows]
