import requests
import os

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "deepseek-r1")

def query_llm(prompt, model=None, stream=False):
    """
    Query Ollama LLM with a prompt and return the response text.
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": stream
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    if stream:
        # For streaming, yield chunks
        for line in resp.iter_lines():
            if line:
                yield line.decode()
    else:
        return resp.json().get("response", "")

def trading_prompt(market_rows, position_rows, cash_balance):
    """
    Build a prompt for the LLM to get trading advice.
    """
    prompt = """
You are a professional trading assistant. Given the following market data, positions, and cash, suggest the next trading action (Buy/Sell/Hold), symbol, and quantity. Respond in JSON like {"action": "Buy/Sell/Hold", "symbol": "...", "quantity": ...}.

Market Data:
"""
    for row in market_rows:
        prompt += f"{row['Symbol']}: {row['Price']}\n"
    prompt += "\nPositions:\n"
    for row in position_rows:
        prompt += f"{row['Symbol']}: qty={row['Quantity']}, price={row['Buy Price']}, market={row['Market Value']}\n"
    prompt += f"\nCash: {cash_balance}\n"
    prompt += "\nWhat is your next action?"
    return prompt

# Example usage:
# from .llm_agent import query_llm, trading_prompt
# advice = query_llm(trading_prompt(market_rows, position_rows, cash_balance))
# print(advice)
