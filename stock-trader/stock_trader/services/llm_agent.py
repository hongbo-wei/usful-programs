import os
import json
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from stock_trader.utils.logger import log_llm_decision

# 路径可根据实际情况调整
MODEL_NAME = "Qwen/Qwen3-235B-A22B-Instruct-2507"
MARKET_DATA_PATH = os.path.join(os.path.dirname(__file__), '../../market_data.csv')

class LLMTraderAgent:
    def __init__(self, model_name=MODEL_NAME):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True, device_map="auto")
        self.pipe = pipeline("text-generation", model=self.model, tokenizer=self.tokenizer, max_new_tokens=256)

    def load_market_data(self):
        import csv
        if not os.path.exists(MARKET_DATA_PATH):
            return []
        with open(MARKET_DATA_PATH, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def build_context(self):
        data = self.load_market_data()
        if not data:
            return ""
        # 只取最近一日期
        latest_date = data[-1]['date']
        latest_rows = [row for row in data if row['date'] == latest_date]
        context = f"市场数据日期: {latest_date}\n"
        for row in latest_rows:
            context += f"{row['symbol']}: 价格={row['price']}, 波动={row['volatility']}, 成交量={row['volume']}\n"
        return context

    def ask(self, user_question):
        context = self.build_context()
        prompt = f"你是一个股票智能体。已知如下市场数据：\n{context}\n请根据这些数据回答：{user_question}"
        result = self.pipe(prompt)
        return result[0]['generated_text'].replace(prompt, '').strip()


def llm_analyze_question(user_question):
    """
    统一入口：处理用户问题，返回大模型分析结果。
    """
    try:
        agent = LLMTraderAgent()
        llm_answer = agent.ask(user_question)
        log_llm_decision(user_question, llm_answer)
        return llm_answer
    except Exception as e:
        return f"模型推理出错: {e}"

# 自动智能分析，无需用户输入Prompt
def auto_llm_analysis():
    """
    自动读取最新market_data.json，调用大模型生成格式化分析建议。
    返回如：建议买入AAPL，xx天后出售，预计升值xxx
    """
    import csv
    market_data_path = MARKET_DATA_PATH
    try:
        with open(market_data_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            return "暂无市场数据，无法分析。"
        # 取最近一条
        latest_row = rows[-1]
        latest_date = latest_row['date']
        # 收集最近5天的日期
        last_dates = [row['date'] for row in rows[-5:]]
        # 收集最新日期的所有symbol数据
        latest_symbols = [row for row in rows if row['date'] == latest_date]
        latest_data_str = '\n'.join([
            f"{r['symbol']}: 价格={r['price']}, 波动={r['volatility']}, 成交量={r['volume']}" for r in latest_symbols
        ])
    except Exception as e:
        return f"读取市场数据失败: {e}"

    prompt = (
        "请根据以下最新市场数据和历史数据，自动分析并给出一个格式化建议，格式如："
        "建议买入AAPL，xx天后出售，预计升值xxx。只输出建议，不要解释。\n"
        f"最新数据:\n{latest_data_str}\n"
        f"历史日期: {last_dates}"
    )

    try:
        answer = llm_analyze_question(prompt)
        return answer.strip()
    except Exception as e:
        return f"模型分析失败: {e}"
# 用法示例：
# agent = LLMTraderAgent()
# answer = agent.ask("当前哪只股票有短期盈利潜力？")
# print(answer)
