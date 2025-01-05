from typing import Dict, Any, Set
import backtrader as bt
from .base_observer import NotificationObserver
from .console_observer import ConsoleObserver

class NotificationManager:
    """通知管理器"""
    
    _observers: Set[NotificationObserver] = set()
    _default_observer = ConsoleObserver()
    
    @classmethod
    def register(cls, observer: NotificationObserver) -> None:
        """注册观察者"""
        cls._observers.add(observer)
    
    @classmethod
    def unregister(cls, observer: NotificationObserver) -> None:
        """注销观察者"""
        cls._observers.discard(observer)
    
    @classmethod
    def clear(cls) -> None:
        """清除所有观察者"""
        cls._observers.clear()
    
    @classmethod
    def set_strategy(cls, strategy: bt.Strategy) -> None:
        """设置策略实例"""
        for observer in cls._get_observers():
            observer.set_strategy(strategy)
    
    @classmethod
    def notify_order(cls, order: bt.Order) -> None:
        """订单通知"""
        for observer in cls._get_observers():
            observer.on_order(order)
    
    @classmethod
    def notify_trade(cls, trade: bt.Trade) -> None:
        """交易通知"""
        for observer in cls._get_observers():
            observer.on_trade(trade)
    
    @classmethod
    def notify_cash(cls, cash: float) -> None:
        """现金变动通知"""
        for observer in cls._get_observers():
            observer.on_cash(cash)
    
    @classmethod
    def notify_store(cls, msg: Dict[str, Any]) -> None:
        """数据源通知"""
        for observer in cls._get_observers():
            observer.on_store(msg)
    
    @classmethod
    def _get_observers(cls) -> Set[NotificationObserver]:
        """获取所有观察者（包括默认观察者）"""
        return cls._observers if cls._observers else {cls._default_observer} 