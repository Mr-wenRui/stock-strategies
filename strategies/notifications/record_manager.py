from typing import Dict, List, Any, Optional
from datetime import datetime
import backtrader as bt
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class TradeRecord:
    """交易记录"""
    def __init__(self, trade: bt.Trade):
        # 交易标识
        self.ref = trade.ref
        self.data = trade.data._name  # 股票代码
        
        # 交易状态
        self.status = trade.status
        self.isclosed = trade.isclosed
        self.isopen = trade.isopen
        self.justopened = trade.justopened
        
        # 交易数据
        self.size = trade.size
        self.price = trade.price
        self.value = trade.value
        self.commission = trade.commission
        self.pnl = trade.pnl
        self.pnlcomm = trade.pnlcomm
        
        # 时间信息
        self.baropen = trade.baropen
        self.barclose = trade.barclose
        self.dtopen = trade.dtopen
        self.dtclose = trade.dtclose
        self.barlen = trade.barlen
        
        # 历史记录
        self.history = trade.history if hasattr(trade, 'history') else []
        
        # 记录时间
        self.record_time = datetime.now()

class OrderRecord:
    """订单记录"""
    def __init__(self, order: bt.Order):
        self.ref = order.ref
        self.status = order.status
        self.size = order.size
        self.price = order.price
        self.pricelimit = order.pricelimit
        self.data = order.data._name
        self.dtcreated = order.created.dt
        self.executed = {
            'size': order.executed.size,
            'price': order.executed.price,
            'value': order.executed.value,
            'comm': order.executed.comm,
            'pnl': order.executed.pnl if hasattr(order.executed, 'pnl') else None,
            'dt': order.executed.dt if hasattr(order.executed, 'dt') else None
        }
        self.record_time = datetime.now()

class CashRecord:
    """现金记录"""
    def __init__(self, cash: float, strategy: bt.Strategy):
        self.cash = cash
        self.value = strategy.broker.getvalue()
        self.datetime = strategy.datetime.datetime()
        init_cash = strategy.broker.startingcash
        self.returns = (self.value / init_cash - 1) * 100
        self.record_time = datetime.now()

class RecordManager:
    """交易记录管理器 (单例模式)"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RecordManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not RecordManager._initialized:
            # 使用列表存储所有交易记录
            self.trade_records: List[TradeRecord] = []
            # 使用字典存储最新的交易状态
            self.active_trades: Dict[int, TradeRecord] = {}
            # 订单和现金记录保持不变
            self.orders: Dict[int, OrderRecord] = {}
            self.cash_history: List[CashRecord] = []
            self.strategy = None
            RecordManager._initialized = True
    
    @classmethod
    def get_instance(cls) -> 'RecordManager':
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def reset(self):
        """重置记录"""
        self.trade_records.clear()
        self.active_trades.clear()
        self.orders.clear()
        self.cash_history.clear()
        self.strategy = None
    
    def set_strategy(self, strategy: bt.Strategy) -> None:
        self.strategy = strategy
    
    def record_trade(self, trade: bt.Trade) -> None:
        """记录交易状态变化"""
        try:
            # 创建新的交易记录
            record = TradeRecord(trade)
            # 添加到历史记录
            self.trade_records.append(record)
            # 更新活动交易状态
            if trade.isclosed:
                self.active_trades.pop(trade.ref, None)
            else:
                self.active_trades[trade.ref] = record
            
            logger.debug(
                f"记录交易 #{trade.ref}: "
                f"状态={record.status}, "
                f"{'已平仓' if record.isclosed else '持仓中'}, "
                f"数量={record.size}, "
                f"价格={record.price:.3f}"
            )
            
        except Exception as e:
            logger.error(f"记录交易失败: {str(e)}")
    
    def record_order(self, order: bt.Order) -> None:
        try:
            record = OrderRecord(order)
            self.orders[order.ref] = record
            logger.debug(f"记录订单 #{order.ref}: {record.__dict__}")
        except Exception as e:
            logger.error(f"记录订单失败: {str(e)}")
    
    def record_cash(self, cash: float) -> None:
        try:
            if self.strategy:
                record = CashRecord(cash, self.strategy)
                self.cash_history.append(record)
                logger.debug(f"记录现金变动: {record.__dict__}")
        except Exception as e:
            logger.error(f"记录现金失败: {str(e)}")
    
    def get_trade_history(self, trade_ref: int = None) -> List[TradeRecord]:
        """获取交易历史记录"""
        if trade_ref is not None:
            return [r for r in self.trade_records if r.ref == trade_ref]
        return self.trade_records
    
    def get_active_trades(self) -> Dict[int, TradeRecord]:
        """获取当前活动的交易"""
        return self.active_trades
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """获取交易统计"""
        try:
            # 获取所有已完成的交易
            closed_trades = [t for t in self.trade_records if t.isclosed]
            if not closed_trades:
                return {}
            
            # 按交易引用分组，只取每个交易的最后一条记录
            unique_trades = {}
            for trade in closed_trades:
                if trade.ref not in unique_trades or \
                   trade.record_time > unique_trades[trade.ref].record_time:
                    unique_trades[trade.ref] = trade
            
            final_trades = list(unique_trades.values())
            total_trades = len(final_trades)
            winning_trades = len([t for t in final_trades if t.pnlcomm > 0])
            losing_trades = len([t for t in final_trades if t.pnlcomm < 0])
            
            total_profit = sum(t.pnlcomm for t in final_trades if t.pnlcomm > 0)
            total_loss = sum(t.pnlcomm for t in final_trades if t.pnlcomm < 0)
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': (winning_trades / total_trades * 100) if total_trades else 0,
                'total_profit': total_profit,
                'total_loss': total_loss,
                'profit_factor': abs(total_profit / total_loss) if total_loss else float('inf'),
                'average_trade': sum(t.pnlcomm for t in final_trades) / total_trades,
                'average_win': total_profit / winning_trades if winning_trades else 0,
                'average_loss': total_loss / losing_trades if losing_trades else 0,
                'largest_win': max((t.pnlcomm for t in final_trades), default=0),
                'largest_loss': min((t.pnlcomm for t in final_trades), default=0),
                'average_bars': sum(t.barlen for t in final_trades) / total_trades
            }
            
        except Exception as e:
            logger.error(f"计算交易统计失败: {str(e)}")
            return {} 