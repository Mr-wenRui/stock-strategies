from typing import Dict, Any
from datetime import datetime
import backtrader as bt
from utils.logger import Logger
from .base_observer import NotificationObserver
from .decorators import record_trade, record_order, record_cash
from .record_manager import RecordManager

logger = Logger.get_logger(__name__)

class ConsoleObserver(NotificationObserver):
    """控制台输出观察者"""
    
    @record_order
    def on_order(self, order: bt.Order) -> None:
        """处理订单通知"""
        # 获取股票代码和交易日期
        data = order.data
        code = data._name
        dt = data.datetime.datetime(0)
        
        logger.debug(f"收到订单通知: {code} - {order.status} at {dt}")
        
        if order.status in [order.Submitted, order.Accepted]:
            logger.debug(f"订单状态更新: {code} - {order.status} at {dt}")
            return
            
        if order.status == order.Completed:
            if order.isbuy():
                msg = (
                    f'买入执行: {code} at {dt} - '
                    f'价格={order.executed.price:.2f}, '
                    f'数量={order.executed.size}, '
                    f'金额={order.executed.value:.2f}, '
                    f'佣金={order.executed.comm:.2f}'
                )
            else:
                # 计算盈亏
                profit = order.executed.pnl if hasattr(order.executed, 'pnl') else 0
                msg = (
                    f'卖出执行: {code} at {dt} - '
                    f'价格={order.executed.price:.2f}, '
                    f'数量={order.executed.size}, '
                    f'金额={order.executed.value:.2f}, '
                    f'佣金={order.executed.comm:.2f}, '
                    f'盈亏={profit:.2f}'
                )
            logger.info(msg)
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.warning(f'订单失败: {code} - {order.status} at {dt}')
    
    @record_trade
    def on_trade(self, trade: bt.Trade) -> None:
        """处理交易通知"""
        # 获取股票代码和当前日期
        data = trade.data
        code = data._name
        current_dt = data.datetime.datetime(0)
        
        # 获取交易记录管理器
        record_manager = RecordManager.get_instance()
        
        # 获取该交易的所有历史记录
        trade_history = record_manager.get_trade_history(trade.ref)
        if not trade_history:
            return
        
        # 获取最新记录
        current_record = trade_history[-1]
        
        # 记录交易状态变化
        status_map = {0: '创建', 1: '开仓', 2: '平仓'}
        logger.debug(
            f"交易状态更新: {code} [#{trade.ref}] - "
            f"状态={status_map.get(current_record.status, '未知')}, "
            f"{'已平仓' if current_record.isclosed else '持仓中'} at {current_dt}"
        )
        
        # 只处理平仓交易
        if not current_record.isclosed:
            return
            
        try:
            # 获取开平仓记录
            open_record = trade_history[0]  # 第一条记录是开仓
            close_record = current_record   # 最后一条记录是平仓
            
            # 获取开平仓时间
            open_dt = bt.num2date(open_record.dtopen) if isinstance(open_record.dtopen, (int, float)) \
                else open_record.dtopen
            close_dt = bt.num2date(close_record.dtclose) if isinstance(close_record.dtclose, (int, float)) \
                else close_record.dtclose
            
            # 提取交易数据
            trade_size = abs(open_record.size)
            open_value = abs(open_record.value)

            
            # 计算收益指标
            commission = sum(record.commission for record in trade_history)  # 累计手续费
            gross_profit = close_record.pnl
            net_profit = close_record.pnlcomm
            returns = (net_profit / open_value) * 100 if open_value != 0 else 0

            
            # 输出交易详情
            logger.info(
                f'交易结束: {code} [#{trade.ref}] - \n'
                f'    时间: {open_dt.strftime("%Y-%m-%d")} -> {close_dt.strftime("%Y-%m-%d")} '
                f'({close_record.barlen}根K线)\n'
                f'    数量: {trade_size}\n'
                f'    手续费: {commission:.2f}\n'
                f'    毛利润: {gross_profit:,.2f}, 净利润: {net_profit:,.2f}\n'
                f'    收益率: {returns:+.2f}%'
            )
            
            # 记录详细的交易历史
            if len(trade_history) > 2:  # 如果有中间状态变化
                logger.debug(
                    f'交易历史 [#{trade.ref}]:\n' + '\n'.join(
                        f'    {i+1}. {record.record_time.strftime("%H:%M:%S")} - '
                        f'价格={record.price:.3f}, '
                        f'持仓变动={record.size:+d}, '
                        f'当前持仓={record.size}, '
                        f'状态={status_map.get(record.status, "未知")}'
                        for i, record in enumerate(trade_history)
                    )
                )
                
        except Exception as e:
            # 如果处理失败，输出基本信息
            logger.info(
                f'交易结束: {code} [#{trade.ref}] at {current_dt} - '
                f'毛利润={current_record.pnl:.2f}, 净利润={current_record.pnlcomm:.2f}'
            )
            logger.debug(f"交易信息处理失败: {str(e)}")
    
    @record_cash
    def on_cash(self, cash: float) -> None:
        """处理现金变动通知"""
        if self.strategy:
            dt = self.strategy.datas[0].datetime.datetime(0)
            portfolio_value = self.strategy.broker.getvalue()
            init_cash = self.strategy.broker.startingcash
            returns = (portfolio_value / init_cash - 1) * 100
            
            logger.info(
                f'现金变动 at {dt}: '
                f'现金={cash:,.2f}, '
                f'总值={portfolio_value:,.2f}, '
                f'收益率={returns:.2f}%'
            )
        else:
            logger.info(f'现金变动: {cash:,.2f}')
    
    def on_store(self, msg: Dict[str, Any]) -> None:
        """处理数据源通知"""
        if self.strategy:
            dt = self.strategy.datas[0].datetime.datetime(0)
            logger.info(f'数据源消息 at {dt}: {msg}')
        else:
            logger.info(f'数据源消息: {msg}') 
    
    def get_trade_summary(self) -> Dict[str, Any]:
        """获取交易统计"""
        return RecordManager.get_instance().get_trade_summary() 