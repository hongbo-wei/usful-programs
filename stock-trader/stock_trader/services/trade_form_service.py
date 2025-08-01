from flask import flash, redirect, url_for
from stock_trader.data import get_stock_price
from stock_trader.services.trade_service import record_trade

def handle_trade_form(form):
    """
    Handle trade form submission logic. Returns a Flask redirect response.
    """
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

def handle_trade_form_errors(form):
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{field}: {error}", "danger")
    return redirect(url_for('dashboard'))
