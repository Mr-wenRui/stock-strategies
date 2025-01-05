from abc import ABC, abstractmethod
from typing import Dict, Any
import backtrader as bt

class NotificationObserver(ABC):
    """通知观察者基类"""
    
    def __init__(self):
        self.strategy = None
    
    def set_strategy(self, strategy: bt.Strategy) -> None:
        """设置策略实例"""
        self.strategy = strategy
    
    @abstractmethod
    def on_order(self, order: bt.Order) -> None:
        """订单通知"""
        pass
    
    @abstractmethod
    def on_trade(self, trade: bt.Trade) -> None:
        """交易通知"""
        pass
    
    @abstractmethod
    def on_cash(self, cash: float) -> None:
        """现金变动通知"""
        pass
    
    @abstractmethod
    def on_store(self, msg: Dict[str, Any]) -> None:
        """数据源通知"""
        pass 