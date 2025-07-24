from flask import Flask, render_template, request, redirect, url_for, flash
from flask_wtf import CSRFProtect
from forms import TradeForm
from stock_trader.services.trade_service import init_db, get_trades, record_trade, calculate_positions_and_pnl
from stock_trader.data import get_stock_price
from stock_trader.models.trade import Trade
from stock_trader.llm_agent import query_llm, trading_prompt

import pandas as pd
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
try:
    font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Medium.ttc')
    plt.rcParams['font.sans-serif'] = ['STHeiti Medium', 'SimHei', 'Arial Unicode MS', 'DejaVu Sans']
except Exception:
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False
import io
import base64




app = Flask(__name__)
import secrets
# 开发环境可自动生成 secret_key，生产环境建议用环境变量
secret_key = os.environ.get('FLASK_SECRET_KEY')
if not secret_key:
    secret_key = secrets.token_urlsafe(32)
app.secret_key = secret_key

# Enable CSRF protection
csrf = CSRFProtect(app)

init_db()

@app.route('/')
def dashboard():
    initial_fund = 1_000_000_000
    trades = get_trades()
    position_rows, cash_balance, position_value, total_asset_value, pnl, roi_str = calculate_positions_and_pnl(trades, initial_fund)
    symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "BTC-USD", "ETH-USD"]
    market_rows = []
    for symbol in symbols:
        price = get_stock_price(symbol)
        market_rows.append({"Symbol": symbol, "Price": price})

    # --- LLM auto-trading logic ---
    import logging
    try:
        llm_prompt = trading_prompt(market_rows, position_rows, cash_balance)
        llm_response = query_llm(llm_prompt, stream=False)
        import json
        if hasattr(llm_response, '__iter__') and not isinstance(llm_response, str):
            llm_response = ''.join([chunk for chunk in llm_response])
        elif isinstance(llm_response, str):
            pass  # already a string
        else:
            llm_response = str(llm_response)
        advice = json.loads(llm_response)
        action = advice.get("action", "").capitalize()
        symbol = advice.get("symbol", "")
        quantity = int(advice.get("quantity", 0))
        valid_symbols = [row["Symbol"] for row in market_rows]
        if action in ["Buy", "Sell"] and symbol in valid_symbols and quantity > 0:
            # Check if already executed this trade in this session (avoid infinite loop)
            from flask import session
            last_trade = session.get("last_llm_trade")
            trade_key = f"{action}:{symbol}:{quantity}"
            if last_trade != trade_key:
                price = get_stock_price(symbol)
                record_trade(symbol, action, quantity, price)
                session["last_llm_trade"] = trade_key
                flash(f"[LLM] {action} {quantity} {symbol} @ ${price} executed.", "success")
    except Exception as e:
        logging.exception("[LLM] Auto-trading error")
        flash(f"[LLM] Auto-trading error: {e}", "danger")

    # 生成股票和加密货币买入总价与市场总价的柱状图
    stock_symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "TSLA"]
    crypto_symbols = ["BTC-USD", "ETH-USD"]
    stock_buy = 0
    stock_market = 0
    crypto_buy = 0
    crypto_market = 0
    for row in position_rows:
        symbol = row["Symbol"]
        buy_cost = row["Buy Price"] * row["Quantity"]
        market_value = row["Market Value"]
        if symbol in stock_symbols:
            stock_buy += buy_cost
            stock_market += market_value
        elif symbol in crypto_symbols:
            crypto_buy += buy_cost
            crypto_market += market_value
    labels = ["Stock", "Crypto"]
    buy_values = [stock_buy, crypto_buy]
    market_values = [stock_market, crypto_market]
    fig, ax = plt.subplots(figsize=(6, 3.5), dpi=120)
    bar_width = 0.35
    x = range(len(labels))
    # 使用更美观的配色
    buy_colors = ["#6EC6FF", "#FFD54F"]  # 蓝色、黄色
    market_colors = ["#AB47BC", "#4DB6AC"]  # 紫色、青色
    ax.bar(x, buy_values, bar_width, label="Buy Total", color=buy_colors, edgecolor="#fff", linewidth=1.5)
    ax.bar([i + bar_width for i in x], market_values, bar_width, label="Market Value", color=market_colors, edgecolor="#fff", linewidth=1.5)
    ax.set_xticks([i + bar_width / 2 for i in x])
    ax.set_xticklabels(labels, fontsize=13, fontweight="bold")
    ax.set_ylabel("USD", fontsize=12)
    ax.set_title("Buy Total vs Market Value", fontsize=15, fontweight="bold", color="#195ca7")
    ax.legend(fontsize=11, loc="upper right", frameon=False)
    ax.grid(axis="y", linestyle="--", alpha=0.18)
    # 美化y轴和去除顶部/右侧边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", transparent=True)
    plt.close(fig)
    asset_bar_chart = base64.b64encode(buf.getvalue()).decode()

    # Position pie chart
    position_pie_chart = None
    if position_rows:
        labels = [row['Symbol'] for row in position_rows]
        sizes = [row['Market Value'] for row in position_rows]
        if any(sizes):
            fig, ax = plt.subplots(figsize=(3.5,3.5), dpi=120)
            colors = plt.cm.Paired(range(len(labels)))
            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, autopct='%1.1f%%', startangle=140,
                colors=colors, textprops={'fontsize':9, 'color':'#222'}, wedgeprops={'edgecolor':'#fff', 'linewidth':1.5, 'alpha':0.95}
            )
            ax.set_title('Position Distribution', fontsize=13, fontweight='bold', color='#195ca7')
            plt.setp(autotexts, size=9, weight='bold', color='#195ca7')
            ax.axis('equal')
            fig.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
            plt.close(fig)
            position_pie_chart = base64.b64encode(buf.getvalue()).decode()

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
        crypto_market=crypto_market
    )


import re
@app.route('/trade', methods=['GET', 'POST'])
def trade():
    symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "BTC-USD", "ETH-USD"]
    form = TradeForm()
    form.symbol.choices = [(s, s) for s in symbols]
    if form.validate_on_submit():
        symbol = form.symbol.data
        trade_type = form.trade_type.data
        quantity = form.quantity.data
        price = get_stock_price(symbol)
        if price is None:
            flash("Failed to fetch price for symbol.", "danger")
            return redirect(url_for('dashboard'))
        record_trade(symbol, trade_type, quantity, price)
        flash(f"{trade_type} {quantity} {symbol} @ ${price} recorded", "success")
        return redirect(url_for('dashboard'))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{field}: {error}", "danger")
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
