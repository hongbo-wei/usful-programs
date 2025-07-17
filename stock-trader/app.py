from flask import Flask, render_template, request, redirect, url_for, flash
from stock_trader.services.trade_service import init_db, get_trades, record_trade
from stock_trader.data import get_stock_price
from stock_trader.models.trade import Trade
import pandas as pd
import os


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
    # 持仓市值
    position_value = 0
    position_rows = []
    for symbol, trade_list in positions.items():
        current_price = get_stock_price(symbol)
        for trade in trade_list:
            market_value = trade.quantity * (current_price if current_price else 0)
            position_value += market_value
            buy_date = trade.timestamp
            try:
                if isinstance(buy_date, str):
                    from datetime import datetime
                    buy_date = datetime.fromisoformat(buy_date)
                buy_date_str = buy_date.strftime('%Y-%m-%d')
            except Exception:
                buy_date_str = str(buy_date)
            position_rows.append({
                "Symbol": symbol,
                "Buy Date": buy_date_str,
                "Buy Price": trade.price,
                "Current Price": current_price,
                "Quantity": trade.quantity,
                "Market Value": market_value,
                "P&L": market_value - trade.quantity * trade.price
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
    # 行情
    symbols = ["AAPL", "NVDA", "MSFT", "AMZN", "META", "GOOGL", "TSLA", "BTC-USD", "ETH-USD"]
    market_rows = []
    for symbol in symbols:
        price = get_stock_price(symbol)
        market_rows.append({"Symbol": symbol, "Price": price})
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
        symbols=symbols
    )

@app.route('/trade', methods=['POST'])
def trade():
    symbol = request.form['symbol']
    trade_type = request.form['trade_type']
    quantity = int(request.form['quantity'])
    price = get_stock_price(symbol)
    record_trade(symbol, trade_type, quantity, price)
    flash(f"{trade_type} {quantity} {symbol} @ ${price} 已记录", "success")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
