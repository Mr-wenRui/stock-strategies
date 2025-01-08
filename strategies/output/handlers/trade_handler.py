from typing import Dict, Any
from utils.logger import Logger
from .base_handler import ResultHandler
from utils.redis_helper import RedisHelper

logger = Logger.get_logger(__name__)

class TradeHandler(ResultHandler):
    """交易信息处理器"""
    
    def __init__(self):
        super().__init__()
        self.stock_info = RedisHelper.get_df('stock:realtime')
        self.current_positions = {}  # 当前持仓
        self.trade_history = []      # 交易历史
    
    def _register_handlers(self) -> None:
        """注册事件处理器"""
        self.subscribe('order', self.handle_order)
        self.subscribe('trade', self.handle_trade)
        self.subscribe('cash', self.handle_cash)
        self.subscribe('analyzer_result', self.handle_analyzer_result)
    
    def handle_order(self, data: Dict[str, Any]) -> None:
        """处理订单事件"""
        try:
            order_type = data['type']
            code = data.get('code', '')
            stock_name = self.stock_info.loc[self.stock_info['代码'] == code, '名称'].values[0]
            
            logger.info("=== 订单信息 ===")
            logger.info(f"订单编号: {data['ref']}")
            logger.info(f"订单类型: {order_type}")
            logger.info(f"股票代码: {code}")
            logger.info(f"股票名称: {stock_name}")
            logger.info(f"交易数量: {data['size']:,} 股")
            logger.info(f"委托价格: ¥{data['price']:.2f}")
            logger.info(f"订单状态: {data['status']}")
            
            # 更新持仓信息
            if data['status'] == 'Completed':
                if order_type == 'Buy':
                    self.current_positions[code] = self.current_positions.get(code, 0) + data['size']
                else:
                    self.current_positions[code] = self.current_positions.get(code, 0) - data['size']
                
                # 记录交易历史
                self.trade_history.append({
                    'time': data.get('time', ''),
                    'code': code,
                    'name': stock_name,
                    'type': order_type,
                    'size': data['size'],
                    'price': data['price']
                })
            
        except Exception as e:
            logger.error(f"处理订单事件失败: {str(e)}")
    
    def handle_trade(self, data: Dict[str, Any]) -> None:
        """处理交易事件"""
        try:
            if data['status'] == 'Closed':
                logger.info("=== 交易结算 ===")
                logger.info("交易盈亏分析:")
                logger.info(f"毛利润: ¥{data['pnl']:,.2f}")
                logger.info(f"净利润: ¥{data['pnlcomm']:,.2f}")
                logger.info(f"手续费: ¥{data['pnl'] - data['pnlcomm']:,.2f}")
                
                # 计算收益率
                if 'cost' in data and data['cost'] > 0:
                    roi = (data['pnlcomm'] / data['cost']) * 100
                    logger.info(f"收益率: {roi:+.2f}%")
                
        except Exception as e:
            logger.error(f"处理交易事件失败: {str(e)}")
    
    def handle_cash(self, data: Dict[str, Any]) -> None:
        """处理资金变动事件"""
        try:
            logger.info("=== 资金状况 ===")
            logger.info(f"可用资金: ¥{data['cash']:,.2f}")
            logger.info(f"总资产: ¥{data['value']:,.2f}")
            
            # 计算持仓市值
            position_value = data['value'] - data['cash']
            position_ratio = (position_value / data['value']) * 100
            logger.info(f"持仓市值: ¥{position_value:,.2f}")
            logger.info(f"仓位比例: {position_ratio:.2f}%")
            
        except Exception as e:
            logger.error(f"处理资金事件失败: {str(e)}")
    
    def handle_analyzer_result(self, data: Dict[str, Any]) -> None:
        """处理分析器结果"""
        try:
            name = data['name']
            result = data['result']
            
            if name == 'trade':
                logger.info("=== 交易统计 ===")
                logger.info("基础统计:")
                logger.info(f"总交易次数: {result.get('total_trades', 0)} 次")
                logger.info(f"盈利交易: {result.get('won', 0)} 次")
                logger.info(f"亏损交易: {result.get('lost', 0)} 次")
                logger.info(f"胜率: {result.get('win_rate', 0):.2f}%")
                
                logger.info("盈亏统计:")
                logger.info(f"盈亏比: {result.get('profit_factor', 0):.2f}")
                logger.info(f"平均盈利: ¥{result.get('average_won', 0):,.2f}")
                logger.info(f"平均亏损: ¥{result.get('average_lost', 0):,.2f}")
                logger.info(f"最大单笔盈利: ¥{result.get('largest_won', 0):,.2f}")
                logger.info(f"最大单笔亏损: ¥{result.get('largest_lost', 0):,.2f}")
                
                # 指标解释
                logger.info("指标说明:")
                logger.info("胜率 - 盈利交易次数占总交易次数的比例")
                logger.info("盈亏比 - 总盈利金额与总亏损金额的比值，大于1表示整体盈利")
                logger.info("平均盈利/亏损 - 单次交易的平均盈亏金额")
                
            elif name == 'drawdown':
                logger.info("=== 回撤分析 ===")
                logger.info(f"最大回撤: {result.get('max_drawdown', 0):.2f}%")
                logger.info(f"当前回撤: {result.get('current_drawdown', 0):.2f}%")
                logger.info("说明: 回撤表示投资组合从峰值下跌的幅度，是衡量风险的重要指标")
                
            elif name == 'sharpe':
                logger.info("=== 夏普比率 ===")
                logger.info(f"夏普比率: {result.get('sharpe_ratio', 0):.2f}")
                logger.info("说明: 夏普比率衡量超额收益与波动率的比值，越高越好，通常大于1即可")
                
        except Exception as e:
            logger.error(f"处理分析器结果失败: {str(e)}")
    
    def print_summary(self) -> None:
        """打印交易总结"""
        try:
            logger.info("========== 交易总结 ==========")
            
            # 打印交易历史
            logger.info("--- 交易记录 ---")
            for trade in self.trade_history:
                logger.info(
                    f"{trade['time']} {trade['type']}: "
                    f"{trade['name']}({trade['code']}) "
                    f"{trade['size']:,}股 @ ¥{trade['price']:.2f}"
                )
            
            # 打印当前持仓
            logger.info("--- 当前持仓 ---")
            for code, size in self.current_positions.items():
                if size > 0:
                    stock_name = self.stock_info.loc[self.stock_info['代码'] == code, '名称'].values[0]
                    logger.info(f"{stock_name}({code}): {size:,}股")
            
        except Exception as e:
            logger.error(f"打印交易总结失败: {str(e)}") 