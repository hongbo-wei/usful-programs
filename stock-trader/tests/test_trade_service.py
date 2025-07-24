import pytest
from stock_trader.services import trade_service
from stock_trader.models.trade import Trade
from datetime import datetime

def test_calculate_positions_and_pnl_basic():
    trades = [
        Trade(id=1, symbol='AAPL', type='Buy', quantity=10, price=100, timestamp=datetime(2024,1,1)),
        Trade(id=2, symbol='AAPL', type='Buy', quantity=10, price=200, timestamp=datetime(2024,1,2)),
        Trade(id=3, symbol='AAPL', type='Sell', quantity=5, price=300, timestamp=datetime(2024,1,3)),
    ]
    # Patch get_stock_price to return a fixed value
    trade_service.get_stock_price = lambda symbol: 400
    position_rows, cash_balance, position_value, total_asset_value, pnl, roi_str = trade_service.calculate_positions_and_pnl(trades, initial_fund=10000)
    assert len(position_rows) == 1
    assert position_rows[0]['Symbol'] == 'AAPL'
    assert position_rows[0]['Quantity'] == 15
    assert position_rows[0]['Buy Price'] == 150.0
    assert position_rows[0]['Current Price'] == 400
    assert cash_balance == 10000 - (10*100+10*200) + (5*300)
    assert position_value == 15*400
    assert total_asset_value == cash_balance + position_value
    assert isinstance(roi_str, str)

def test_get_trades_handles_db_error(monkeypatch):
    monkeypatch.setattr(trade_service, 'DB_NAME', '/invalid/path/to/db')
    trades = trade_service.get_trades()
    assert trades == []
