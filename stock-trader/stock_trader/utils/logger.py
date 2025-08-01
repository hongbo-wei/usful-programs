import os
import logging
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), '../../logs')
LOG_PATH = os.path.join(LOG_DIR, 'trading.log')

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    encoding='utf-8'
)

def log_trade_action(action, symbol, quantity, price, reason=None):
    msg = f"TRADE: {action} {quantity} {symbol} @ {price}"
    if reason:
        msg += f" | Reason: {reason}"
    logging.info(msg)

def log_llm_decision(question, answer):
    logging.info(f"LLM: Q: {question} | A: {answer}")

def get_recent_logs(n=50):
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    return lines[-n:]
