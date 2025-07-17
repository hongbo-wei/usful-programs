from dataclasses import dataclass
from datetime import datetime

@dataclass
class Trade:
    id: int
    symbol: str
    type: str  # 'Buy' or 'Sell'
    quantity: int
    price: float
    timestamp: datetime
