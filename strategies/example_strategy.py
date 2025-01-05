from typing import Dict, Any, Type
import backtrader as bt
from .base_strategy import BaseStrategy
from utils.logger import Logger
from .observers.base_observer import BaseObserver
from .observers.custom_observers import (
    ReturnsObserver
)

logger = Logger.get_logger(__name__)

class ExampleStrategy(BaseStrategy):
    """示例策略"""
    
    params = (
        ('fast_period', 5),     # 快速均线周期
        ('slow_period', 15),    # 慢速均线周期
        ('position_pct', 0.2),  # 单个股票最大仓位
        ('max_positions', 5),   # 最大持仓数量
        ('stop_loss', 0.05),    # 止损比例
        ('take_profit', 0.1),   # 止盈比例
    )
    
    def __init__(self):
        """初始化策略"""
        super(ExampleStrategy, self).__init__()
        
        # 计算技术指标
        self.fast_ma = {}
        self.slow_ma = {}
        self.crossover = {}
        self.rsi = {}
        
        for data in self.datas:
            # 计算快速和慢速移动平均线
            self.fast_ma[data._name] = bt.indicators.SMA(
                data.close, period=self.p.fast_period
            )
            self.slow_ma[data._name] = bt.indicators.SMA(
                data.close, period=self.p.slow_period
            )
            
            # 计算均线交叉
            self.crossover[data._name] = bt.indicators.CrossOver(
                self.fast_ma[data._name],
                self.slow_ma[data._name]
            )
            
            # 计算RSI
            self.rsi[data._name] = bt.indicators.RSI(
                data.close, period=14
            )
    
    def get_latest_metrics(self) -> Dict[str, float]:
        """获取最新指标"""
        try:
            def get_latest(observer_type: Type[BaseObserver], line_name: str) -> float:
                return self.get_latest_observer_value(observer_type, line_name)
            
            return {
                'returns': get_latest(ReturnsObserver, 'returns')
            }
        except Exception as e:
            logger.error(f"获取指标失败: {str(e)}")
            return {}
    
    def get_metrics_analysis(self) -> Dict[str, Any]:
        """获取指标分析结果"""
        try:
            return {
                'returns': self.get_observer_analysis(ReturnsObserver)
            }
        except Exception as e:
            logger.error(f"获取指标分析失败: {str(e)}")
            return {}
    
    def _next(self):
        """策略主逻辑"""
        try:
            # 获取最新指标
            metrics = self.get_latest_metrics()
            
            # 记录当前状态
            self.log(f"当前指标: {metrics}")
            self.log(f"当前现金: {self.broker.getcash():,.2f}")
            
            # 风险控制（适当放宽限制）
            if metrics.get('drawdown', 0) > 20:  # 回撤超过20%
                self.log(f"当前回撤: {metrics['drawdown']:.2f}%，减少仓位")
                self.reduce_positions()
                return
            
            # 交易信号处理
            active_positions = len([d for d in self.datas if self.getposition(d).size > 0])
            self.log(f"当前持仓数: {active_positions}")
            
            for data in self.datas:
                pos = self.getposition(data).size
                
                # 记录技术指标
                self.log(f"{data._name} - "
                        f"Fast MA: {self.fast_ma[data._name][0]:.2f}, "
                        f"Slow MA: {self.slow_ma[data._name][0]:.2f}, "
                        f"RSI: {self.rsi[data._name][0]:.2f}, "
                        f"Cross: {self.crossover[data._name][0]}")
                
                if pos > 0:  # 持仓状态
                    # 检查止盈止损
                    self.check_exit_signals(data)
                    
                    # 均线死叉且RSI超买，或RSI严重超买
                    if (self.crossover[data._name] < 0 and self.rsi[data._name] > 65) or \
                       self.rsi[data._name] > 75:
                        self.process_sell_signal(data)
                
                elif active_positions < self.p.max_positions:  # 可以开新仓
                    # 均线金叉且RSI未超买，或RSI超卖
                    if (self.crossover[data._name] > 0 and self.rsi[data._name] < 65) or \
                       self.rsi[data._name] < 30:
                        self.process_buy_signal(data)
                    
        except Exception as e:
            self.log(f"交易执行失败: {str(e)}")
    
    def check_exit_signals(self, data):
        """检查退出信号"""
        try:
            pos = self.getposition(data)
            if not pos.size:
                return
                
            # 计算浮动盈亏
            unrealized_pnl = (data.close[0] - pos.price) / pos.price
            self.log(f"{data._name} 当前浮动盈亏: {unrealized_pnl:.2%}")
            
            # 止损（放宽一些）
            if unrealized_pnl < -self.p.stop_loss:
                self.sell(data=data, size=pos.size)
                self.log(f'止损: {data._name}, 亏损={unrealized_pnl:.2%}')
                
            # 止盈（分批）
            elif unrealized_pnl > self.p.take_profit:
                # 先卖出一半
                size = (pos.size // 2 // 100) * 100
                if size > 0:
                    self.sell(data=data, size=size)
                    self.log(f'止盈: {data._name}, 盈利={unrealized_pnl:.2%}, 卖出数量={size}')
                
        except Exception as e:
            self.log(f"检查退出信号失败: {str(e)}")
    
    def process_buy_signal(self, data):
        """处理买入信号"""
        try:
            # 计算可用资金
            available_cash = self.broker.getcash()
            if available_cash < 10000:  # 提高最低现金要求
                self.log(f"可用资金不足: {available_cash:,.2f}")
                return
            
            # 计算目标仓位金额
            portfolio_value = self.broker.getvalue()
            target_value = min(
                available_cash * self.p.position_pct,
                portfolio_value * self.p.position_pct
            )
            
            # 计算可买数量
            price = data.close[0]
            size = int(target_value / (price * (1 + self.p.commission)))
            size = (size // 100) * 100  # 确保是100的整数倍
            
            if size >= 100:  # 至少买入1手
                self.buy(data=data, size=size)
                self.log(f'买入信号 - {data._name}: '
                        f'数量={size}, 价格={price:.2f}, '
                        f'金额={size*price:,.2f}')
                
        except Exception as e:
            self.log(f"买入信号处理失败: {str(e)}")
    
    def process_sell_signal(self, data):
        """处理卖出信号"""
        try:
            pos = self.getposition(data).size
            if pos > 0:
                self.sell(data=data, size=pos)
                self.log(f'卖出: {data._name}, 数量={pos}, 价格={data.close[0]:.2f}')
                
        except Exception as e:
            self.log(f"卖出信号处理失败: {str(e)}")
    
    def reduce_positions(self):
        """减少持仓"""
        try:
            for data in self.datas:
                pos = self.getposition(data).size
                if pos > 0:
                    # 减仓一半
                    size = (pos // 2 // 100) * 100
                    if size > 0:
                        self.sell(data=data, size=size)
                        self.log(f'减仓 - {data._name}: 数量={size}')
                        
        except Exception as e:
            self.log(f"减仓失败: {str(e)}")
    
    def ensure_cash_buffer(self):
        """确保现金缓冲"""
        try:
            target_cash = self.broker.getvalue() * 0.2  # 目标现金比例20%
            current_cash = self.broker.getcash()
            
            if current_cash < target_cash:
                for data in self.datas:
                    pos = self.getposition(data).size
                    if pos > 0:
                        # 计算需要卖出的数量
                        price = data.close[0]
                        needed_cash = target_cash - current_cash
                        size = int(needed_cash / price)
                        size = min(size, pos)  # 不超过持仓量
                        size = (size // 100) * 100  # 确保是100的整数倍
                        
                        if size > 0:
                            self.sell(data=data, size=size)
                            self.log(f'现金缓冲 - {data._name}: 卖出={size}')
                            
        except Exception as e:
            self.log(f"现金缓冲调整失败: {str(e)}")
    
    def adjust_position_size(self):
        """调整持仓规模"""
        try:
            # 当胜率低时，减小单次交易规模
            self.p.position_pct = max(0.1, self.p.position_pct * 0.8)
            self.log(f"调整持仓比例至: {self.p.position_pct:.1%}")
            
        except Exception as e:
            self.log(f"持仓规模调整失败: {str(e)}")

if __name__ == '__main__':
    print("请使用 run_strategy.py 运行策略")
