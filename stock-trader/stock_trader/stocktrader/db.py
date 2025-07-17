import sqlite3
import pandas as pd

DB_NAME = 'stock_trader/data/trades.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        type TEXT,
        quantity INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def record_trade(symbol, trade_type, quantity):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('INSERT INTO trades (symbol, type, quantity) VALUES (?, ?, ?)', (symbol, trade_type, quantity))
    conn.commit()
    conn.close()

def get_trades():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query('SELECT * FROM trades ORDER BY timestamp DESC', conn)
    conn.close()
    return df
