import os
from stock_trader.utils.logger import log_trade_action, log_llm_decision
from stock_trader.services.trade_service import execute_trade

def auto_trade_by_llm_decision(llm_answer, symbols):
    """
    解析大模型输出，若建议买/卖，自动执行模拟交易。
    llm_answer: str, symbols: list
    """
    # 简单规则：如果模型建议买/卖某只已知股票，则自动下单
    for symbol in symbols:
        if symbol in llm_answer:
            if '买' in llm_answer or 'buy' in llm_answer.lower():
                # 假设买1股，价格用当前市场价
                price = None  # 你可以集成实时价格
                execute_trade(symbol, 'Buy', 1, price)
                log_trade_action('Buy', symbol, 1, price, reason='LLM建议')
                return f"已根据智能体建议买入1股 {symbol}"
            if '卖' in llm_answer or 'sell' in llm_answer.lower():
                price = None
                execute_trade(symbol, 'Sell', 1, price)
                log_trade_action('Sell', symbol, 1, price, reason='LLM建议')
                return f"已根据智能体建议卖出1股 {symbol}"
    return None
