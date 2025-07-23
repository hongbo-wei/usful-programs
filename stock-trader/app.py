from flask import Flask, render_template, request, redirect, url_for, flash
from stock_trader.services.trade_service import init_db, get_trades, record_trade
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
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev')
init_db()

@app.route('/')
def dashboard():
    initial_fund = 1_000_000_000
    trades = get_trades()
    positions = {}
    total_buy_cost = 0
    total_sell_income = 0
    for t in trades:
        if t.type == 'Buy':
            positions.setdefault(t.symbol, []).append(t)
            total_buy_cost += t.quantity * t.price
        elif t.type == 'Sell':
            total_sell_income += t.quantity * t.price
    # Position value
    position_value = 0
    position_rows = []
    from collections import defaultdict
    # Merge same symbol positions
    merged = defaultdict(lambda: {"total_qty":0, "total_cost":0, "first_date":None})
    for symbol, trade_list in positions.items():
        for trade in trade_list:
            merged[symbol]["total_qty"] += trade.quantity
            merged[symbol]["total_cost"] += trade.quantity * trade.price
            if merged[symbol]["first_date"] is None or trade.timestamp < merged[symbol]["first_date"]:
                merged[symbol]["first_date"] = trade.timestamp
    for symbol, data in merged.items():
        qty = data["total_qty"]
        avg_price = data["total_cost"] / qty if qty else 0
        buy_date = data["first_date"]
        try:
            if isinstance(buy_date, str):
                from datetime import datetime
                buy_date = datetime.fromisoformat(buy_date)
            buy_date_str = buy_date.strftime('%Y-%m-%d')
        except Exception:
            buy_date_str = str(buy_date)
        current_price = get_stock_price(symbol)
        market_value = qty * (current_price if current_price else 0)
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
        position_value = 0
        total_asset_value = initial_fund
    pnl = total_asset_value - initial_fund
    roi = (pnl / initial_fund) * 100 if initial_fund else 0
    roi_str = f"{roi:.4f}%"
    # Market quotes
    symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "BTC-USD", "ETH-USD"]
    market_rows = []
    for symbol in symbols:
        price = get_stock_price(symbol)
        market_rows.append({"Symbol": symbol, "Price": price})

    # --- LLM auto-trading logic ---
    try:
        llm_prompt = trading_prompt(market_rows, position_rows, cash_balance)
        llm_response = query_llm(llm_prompt, stream=False)
        import json
        if hasattr(llm_response, '__iter__') and not isinstance(llm_response, str):
            llm_response = ''.join([chunk for chunk in llm_response])
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
        flash(f"[LLM] Auto-trading error: {e}", "danger")

    # Net worth curve
    net_worth_chart = None
    pnl_line_chart = None
    plt.style.use('seaborn-v0_8-darkgrid')
    df = None
    if hasattr(trades, 'to_dict'):
        df = trades if isinstance(trades, pd.DataFrame) else pd.DataFrame([t.__dict__ for t in trades])
    if df is not None and not df.empty:
        df = df.sort_values('timestamp')
        # 只保留2025-07-17及之后的数据
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df[df['timestamp'] >= pd.Timestamp('2025-07-17')]
        if not df.empty:
            df['amount'] = df.apply(lambda x: x['quantity'] * x['price'] * (1 if x['type']=='Buy' else -1), axis=1)
            df['net'] = initial_fund - df['amount'].cumsum()
            df['net'] += df.apply(lambda x: x['quantity'] * get_stock_price(x['symbol']) if x['type']=='Buy' else 0, axis=1).cumsum()
            # 生成每日累计P&L（已实现的盈亏）
            df['date'] = df['timestamp'].dt.date
            # 计算每日已实现P&L
            daily_realized = df.groupby('date').apply(lambda x: x[x['type']=='Sell']['amount'].sum() + x[x['type']=='Buy']['amount'].sum())
            # 累计P&L
            daily_pnl = daily_realized.cumsum()
            # x轴补齐：从2025-07-17到最后一天
            import datetime
            start_date = datetime.date(2025, 7, 17)
            end_date = df['date'].max()
            all_dates = pd.date_range(start=start_date, end=end_date, freq='D').date
            daily_pnl = daily_pnl.reindex(all_dates, method=None).fillna(method='ffill').fillna(0)
            # 净值曲线也补齐x轴
            net_curve = df.set_index('date')['net'].reindex(all_dates, method='ffill').fillna(initial_fund)
            # P&L折线图
            fig2, ax2 = plt.subplots(figsize=(5,2.5), dpi=120)
            ax2.plot(all_dates, daily_pnl.values, marker='o', color='#d32f2f', linewidth=2, label='P&L')
            ax2.set_title('P&L Curve', fontsize=13, fontweight='bold', color='#d32f2f')
            ax2.set_xlabel('Date', fontsize=10)
            ax2.set_ylabel('P&L', fontsize=10)
            ax2.tick_params(axis='x', rotation=30, labelsize=8)
            import matplotlib.dates as mdates
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
            fig2.autofmt_xdate()
            ax2.grid(True, linestyle='--', alpha=0.4)
            ax2.legend(frameon=False, loc='upper left', fontsize=9)
            fig2.tight_layout()
            buf2 = io.BytesIO()
            plt.savefig(buf2, format='png', bbox_inches='tight', transparent=True)
            plt.close(fig2)
            pnl_line_chart = base64.b64encode(buf2.getvalue()).decode()
            # 净值曲线
            fig, ax = plt.subplots(figsize=(5,2.5), dpi=120)
            ax.plot(all_dates, net_curve.values, marker='o', color='#2a7be4', linewidth=2, label='Net Worth')
            ax.fill_between(all_dates, net_curve.values, color='#e3f0ff', alpha=0.5)
            ax.set_title('Net Worth Curve', fontsize=13, fontweight='bold', color='#195ca7')
            ax.set_xlabel('Date', fontsize=10)
            ax.set_ylabel('Net Worth', fontsize=10)
            ax.tick_params(axis='x', rotation=30, labelsize=8)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            fig.autofmt_xdate()
            ax.grid(True, linestyle='--', alpha=0.4)
            ax.legend(frameon=False, loc='upper left', fontsize=9)
            fig.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
            plt.close(fig)
            net_worth_chart = base64.b64encode(buf.getvalue()).decode()
        else:
            # 没有数据，画空图
            import datetime
            fig, ax = plt.subplots(figsize=(5,2.5), dpi=120)
            now = datetime.datetime.now()
            times = [now - datetime.timedelta(days=1), now]
            values = [initial_fund, initial_fund]
            ax.plot(times, values, marker='o', color='#2a7be4', linewidth=2, label='Net Worth')
            ax.fill_between(times, values, color='#e3f0ff', alpha=0.5)
            ax.set_title('Net Worth Curve', fontsize=13, fontweight='bold', color='#195ca7')
            ax.set_xlabel('Time', fontsize=10)
            ax.set_ylabel('Net Worth', fontsize=10)
            ax.tick_params(axis='x', rotation=30, labelsize=8)
            ax.grid(True, linestyle='--', alpha=0.4)
            ax.legend(frameon=False, loc='upper left', fontsize=9)
            fig.tight_layout()
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
            plt.close(fig)
            net_worth_chart = base64.b64encode(buf.getvalue()).decode()
            # 空P&L图
            fig2, ax2 = plt.subplots(figsize=(5,2.5), dpi=120)
            ax2.plot(times, [0,0], marker='o', color='#d32f2f', linewidth=2, label='P&L')
            ax2.set_title('P&L Curve', fontsize=13, fontweight='bold', color='#d32f2f')
            ax2.set_xlabel('Date', fontsize=10)
            ax2.set_ylabel('P&L', fontsize=10)
            ax2.tick_params(axis='x', rotation=30, labelsize=8)
            ax2.grid(True, linestyle='--', alpha=0.4)
            ax2.legend(frameon=False, loc='upper left', fontsize=9)
            fig2.tight_layout()
            buf2 = io.BytesIO()
            plt.savefig(buf2, format='png', bbox_inches='tight', transparent=True)
            plt.close(fig2)
            pnl_line_chart = base64.b64encode(buf2.getvalue()).decode()
    else:
        # No trades, show flat line
        import datetime
        fig, ax = plt.subplots(figsize=(5,2.5), dpi=120)
        now = datetime.datetime.now()
        times = [now - datetime.timedelta(days=1), now]
        values = [initial_fund, initial_fund]
        ax.plot(times, values, marker='o', color='#2a7be4', linewidth=2, label='Net Worth')
        ax.fill_between(times, values, color='#e3f0ff', alpha=0.5)
        ax.set_title('Net Worth Curve', fontsize=13, fontweight='bold', color='#195ca7')
        ax.set_xlabel('Time', fontsize=10)
        ax.set_ylabel('Net Worth', fontsize=10)
        ax.tick_params(axis='x', rotation=30, labelsize=8)
        ax.grid(True, linestyle='--', alpha=0.4)
        ax.legend(frameon=False, loc='upper left', fontsize=9)
        fig.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
        plt.close(fig)
        net_worth_chart = base64.b64encode(buf.getvalue()).decode()
        # 空P&L图
        fig2, ax2 = plt.subplots(figsize=(5,2.5), dpi=120)
        ax2.plot(times, [0,0], marker='o', color='#d32f2f', linewidth=2, label='P&L')
        ax2.set_title('P&L Curve', fontsize=13, fontweight='bold', color='#d32f2f')
        ax2.set_xlabel('Date', fontsize=10)
        ax2.set_ylabel('P&L', fontsize=10)
        ax2.tick_params(axis='x', rotation=30, labelsize=8)
        ax2.grid(True, linestyle='--', alpha=0.4)
        ax2.legend(frameon=False, loc='upper left', fontsize=9)
        fig2.tight_layout()
        buf2 = io.BytesIO()
        plt.savefig(buf2, format='png', bbox_inches='tight', transparent=True)
        plt.close(fig2)
        pnl_line_chart = base64.b64encode(buf2.getvalue()).decode()

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
        net_worth_chart=net_worth_chart,
        position_pie_chart=position_pie_chart,
        pnl_line_chart=pnl_line_chart
    )

@app.route('/trade', methods=['POST'])
def trade():
    symbol = request.form['symbol']
    trade_type = request.form['trade_type']
    quantity = int(request.form['quantity'])
    price = get_stock_price(symbol)
    record_trade(symbol, trade_type, quantity, price)
    flash(f"{trade_type} {quantity} {symbol} @ ${price} recorded", "success")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
