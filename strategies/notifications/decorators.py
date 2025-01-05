from functools import wraps
from typing import Callable
from datetime import datetime
from .record_manager import RecordManager

def record_trade(func: Callable):
    @wraps(func)
    def wrapper(self, trade, *args, **kwargs):
        record_manager = RecordManager.get_instance()
        if record_manager.strategy is None:
            record_manager.set_strategy(self.strategy)
        # 检查是否已经记录过这个状态
        existing_records = record_manager.get_trade_history(trade.ref)
        if not existing_records or \
           existing_records[-1].status != trade.status or \
           existing_records[-1].isclosed != trade.isclosed:
            record_manager.record_trade(trade)
        return func(self, trade, *args, **kwargs)
    return wrapper

def record_order(func: Callable):
    @wraps(func)
    def wrapper(self, order, *args, **kwargs):
        record_manager = RecordManager.get_instance()
        if record_manager.strategy is None:
            record_manager.set_strategy(self.strategy)
        # 检查是否已经记录过这个状态
        if order.ref not in record_manager.orders or \
           record_manager.orders[order.ref].status != order.status:
            record_manager.record_order(order)
        return func(self, order, *args, **kwargs)
    return wrapper

def record_cash(func: Callable):
    @wraps(func)
    def wrapper(self, cash, *args, **kwargs):
        record_manager = RecordManager.get_instance()
        if record_manager.strategy is None:
            record_manager.set_strategy(self.strategy)
        # 检查是否需要记录新的现金变动
        if (not record_manager.cash_history or 
            (datetime.now() - record_manager.cash_history[-1].record_time).total_seconds() > 1):
            record_manager.record_cash(cash)
        return func(self, cash, *args, **kwargs)
    return wrapper 