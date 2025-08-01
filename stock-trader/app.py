from flask import render_template, Flask, request, redirect, url_for, flash, jsonify
from flask_wtf import CSRFProtect
from forms import TradeForm
import os
import secrets
from stock_trader.services.trade_service import init_db, get_trades, calculate_positions_and_pnl
from stock_trader.services.llm_trading import llm_auto_trade
from stock_trader.services.llm_agent import LLMTraderAgent
from stock_trader.services.trading_executor import auto_trade_by_llm_decision
from stock_trader.utils.logger import log_llm_decision, get_recent_logs
from stock_trader.utils.market import get_symbols, get_market_rows, summarize_asset_values
from stock_trader.utils.market_data import fetch_market_data, append_market_data_csv
from stock_trader.utils.chart import generate_asset_bar_chart, generate_position_pie_chart
from stock_trader.services.trade_form_service import handle_trade_form, handle_trade_form_errors
from flask_wtf.csrf import CSRFError


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    # 开发环境可自动生成 secret_key，生产环境建议用环境变量
    secret_key = os.environ.get('FLASK_SECRET_KEY')
    if not secret_key:
        secret_key = secrets.token_urlsafe(32)
    app.secret_key = secret_key
    # Enable CSRF protection
    csrf = CSRFProtect(app)
    app.csrf = csrf  # 方便全局访问
    return app

app = create_app()

init_db()

@app.route('/')
def dashboard():
    initial_fund = 1_000_000_000
    trades = get_trades()
    position_rows, cash_balance, position_value, total_asset_value, pnl, roi_str = calculate_positions_and_pnl(trades, initial_fund)
    symbols = get_symbols()
    market_rows = get_market_rows(symbols)


    # 每次刷新时获取最新市场数据并追加到 market_data.json
    market_data = fetch_market_data(symbols)
    append_market_data_csv(market_data, os.path.join(os.path.dirname(__file__), 'market_data.csv'))


    # 智能分析：不自动调用，由按钮触发
    llm_answer = None
    user_question = None
    auto_trade_result = request.args.get('auto_trade_result')

    logs = get_recent_logs(50)
    stock_buy, stock_market, crypto_buy, crypto_market = summarize_asset_values(position_rows)
    asset_bar_chart = generate_asset_bar_chart(stock_buy, stock_market, crypto_buy, crypto_market)
    position_pie_chart = generate_position_pie_chart(position_rows)

    return render_template(
        'dashboard.html',
        initial_fund=initial_fund,
        cash_balance=cash_balance,
        position_value=position_value,
        total_asset_value=total_asset_value,
        pnl=pnl,
        roi=roi_str,
        market_rows=market_rows,
        position_rows=position_rows,
        trades=trades,
        symbols=symbols,
        asset_bar_chart=asset_bar_chart,
        position_pie_chart=position_pie_chart,
        stock_buy=stock_buy,
        stock_market=stock_market,
        crypto_buy=crypto_buy,
        crypto_market=crypto_market,
        llm_answer=llm_answer,
        user_question=user_question,
        auto_trade_result=auto_trade_result,
        logs=logs
    )

@app.route('/llm_analysis', methods=['POST'])
@app.csrf.exempt
def llm_analysis():
    from stock_trader.services.llm_agent import auto_llm_analysis
    answer = auto_llm_analysis()
    return jsonify({'llm_answer': answer})

@app.route('/auto_trade', methods=['POST'])
def auto_trade():
    symbols = get_symbols()
    user_question = request.form.get('question')
    llm_answer = request.form.get('llm_answer')
    from stock_trader.services.trading_executor import auto_trade_by_llm_decision
    auto_trade_result = auto_trade_by_llm_decision(llm_answer, symbols)
    return redirect(url_for('dashboard', question=user_question, auto_trade_result=auto_trade_result))

@app.route('/trade', methods=['GET', 'POST'])
def trade():
    symbols = get_symbols()
    form = TradeForm()
    form.symbol.choices = [(s, s) for s in symbols]
    if form.validate_on_submit():
        return handle_trade_form(form)
    else:
        return handle_trade_form_errors(form)

def main():
    app.run(debug=True)

if __name__ == '__main__':
    main()
