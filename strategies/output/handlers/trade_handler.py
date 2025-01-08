from typing import Dict, Any
from utils.logger import Logger
from .base_handler import ResultHandler

logger = Logger.get_logger(__name__)

class TradeHandler(ResultHandler):
    """交易事件处理器"""
    
    def _register_handlers(self) -> None:
        """注册事件处理器"""
        self.subscribe('order', self.handle_order)
        self.subscribe('trade', self.handle_trade)
        self.subscribe('cash', self.handle_cash)
        self.subscribe('store', self.handle_store)
    
    def handle_order(self, order: Dict[str, Any]) -> None:
        """处理订单事件"""
        if order['status'] in ['Completed', 'Canceled', 'Margin']:
            logger.info(f"订单 {order['ref']} {order['status']}: "
                       f"{order['type']} {order['size']} @ {order['price']:.2f}")
    
    def handle_trade(self, trade: Dict[str, Any]) -> None:
        """处理交易事件"""
        if trade['status'] == 'Closed':
            logger.info(f"交易完成: {trade['pnl']:,.2f} ({trade['pnlcomm']:,.2f})")
    
    def handle_cash(self, data: Dict[str, Any]) -> None:
        """处理现金变动事件"""
        logger.info(f"现金变动: {data['cash']:,.2f}, 总值: {data['value']:,.2f}")
    
    def handle_store(self, msg: str) -> None:
        """处理数据源事件"""
        logger.info(f"数据源通知: {msg}") 