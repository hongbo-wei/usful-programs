
import os
import csv
from datetime import datetime
import yfinance as yf

def fetch_market_data(symbols):
    data = {}
    for symbol in symbols:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        data[symbol] = {
            'price': info.get('regularMarketPrice'),
            'volatility': info.get('regularMarketDayHigh', 0) - info.get('regularMarketDayLow', 0),
            'volume': info.get('regularMarketVolume'),
            'timestamp': datetime.utcnow().isoformat()
        }
    return data


def append_market_data_csv(new_data, file_path):
    """
    Appends new market data to a CSV file. Each row: date, symbol, price, volatility, volume, timestamp
    """
    fieldnames = ['date', 'symbol', 'price', 'volatility', 'volume', 'timestamp']
    date_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    file_exists = os.path.exists(file_path)
    with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if not file_exists or os.stat(file_path).st_size == 0:
            writer.writeheader()
        for symbol, info in new_data.items():
            writer.writerow({
                'date': date_str,
                'symbol': symbol,
                'price': info.get('price'),
                'volatility': info.get('volatility'),
                'volume': info.get('volume'),
                'timestamp': info.get('timestamp')
            })
