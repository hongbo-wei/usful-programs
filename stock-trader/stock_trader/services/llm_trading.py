import logging
import json
from flask import session, flash

from stock_trader.data import get_stock_price
from stock_trader.services.trade_service import record_trade

def llm_auto_trade(market_rows, position_rows, cash_balance):
    """
    Handles LLM-based auto-trading logic. Returns a tuple (success, message).
    """
    try:
        llm_prompt = trading_prompt(market_rows, position_rows, cash_balance)
        llm_response = query_llm(llm_prompt, stream=False)
        # 修复类型判断，防止字符串被遍历
        if isinstance(llm_response, str):
            pass  # already a string
        elif hasattr(llm_response, '__iter__'):
            llm_response = ''.join([chunk for chunk in llm_response])
        else:
            llm_response = str(llm_response)
        advice = json.loads(llm_response)
        action = advice.get("action", "").capitalize()
        symbol = advice.get("symbol", "")
        quantity = int(advice.get("quantity", 0))
        valid_symbols = [row["Symbol"] for row in market_rows]
        if action in ["Buy", "Sell"] and symbol in valid_symbols and quantity > 0:
            last_trade = session.get("last_llm_trade")
            trade_key = f"{action}:{symbol}:{quantity}"
            if last_trade != trade_key:
                price = get_stock_price(symbol)
                record_trade(symbol, action, quantity, price)
                session["last_llm_trade"] = trade_key
                flash(f"[LLM] {action} {quantity} {symbol} @ ${price} executed.", "success")
                return True, f"[LLM] {action} {quantity} {symbol} @ ${price} executed."
        return False, "No valid LLM trade executed."
    except Exception as e:
        logging.exception("[LLM] Auto-trading error")
        flash(f"[LLM] Auto-trading error: {e}", "danger")
        return False, f"[LLM] Auto-trading error: {e}"
