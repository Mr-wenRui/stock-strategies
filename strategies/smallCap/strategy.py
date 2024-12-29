import backtrader as bt
import numpy as np
from datetime import datetime, timedelta
from strategies.smallCap.data_loader import DataLoader

class SmallCapStrategy(bt.Strategy):
    """改进的小市值策略"""
    
    params = (
        ('market_cap_percentile', 20),    # 选择市值最小的20%的股票
        ('holding_period', 20),           # 持有20个交易日
        ('max_position_per_stock', 0.1),  # 单只股票最大仓位
        ('min_amount_ma', 1000000),       # 最小成交额均值(万元)
        ('max_drawdown_threshold', 0.15),  # 最大回撤阈值
        ('min_turnover_rate', 1.0)        # 最小换手率(%)
    )
    
    def __init__(self):
        self.data_loader = DataLoader()
        self.market_caps = {}
        self.holding_days = {}
        self.order_list = []
        self.entry_prices = {}
        
        # 计算成交额均值
        self.amount_ma = {}
        for data in self.datas:
            self.amount_ma[data._name] = bt.indicators.SMA(
                data.amount, period=20
            )
    
    def next(self):
        # 更新持仓天数
        for data in self.datas:
            if self.getposition(data).size > 0:
                self.holding_days[data._name] = self.holding_days.get(data._name, 0) + 1
        
        # 记录所有股票的市值（满足成交额和换手率条件）
        for data in self.datas:
            if (self.amount_ma[data._name][0] >= self.p.min_amount_ma and 
                data.turnover_rate[0] >= self.p.min_turnover_rate):
                self.market_caps[data._name] = data.market_cap[0]
        
        # 检查是否需要调仓
        if len(self.market_caps) == len(self.datas):
            self._rebalance_portfolio()
    
    def _rebalance_portfolio(self):
        """调仓逻辑"""
        # 获取市值最小的股票
        sorted_stocks = sorted(self.market_caps.items(), key=lambda x: x[1])
        num_stocks = int(len(sorted_stocks) * self.params.market_cap_percentile / 100)
        target_stocks = sorted_stocks[:num_stocks]
        
        # 平仓逻辑
        for data in self.datas:
            position = self.getposition(data)
            if position.size > 0:
                # 平仓条件：
                # 1. 不在目标池中
                # 2. 持仓时间超过holding_period
                # 3. 单只股票跌幅超过阈值
                if (data._name not in [stock[0] for stock in target_stocks] or
                    self.holding_days.get(data._name, 0) >= self.p.holding_period or
                    (data.close[0] / self.entry_prices[data._name] - 1) <= -self.p.max_drawdown_threshold):
                    self.close(data)
                    if data._name in self.holding_days:
                        del self.holding_days[data._name]
                    if data._name in self.entry_prices:
                        del self.entry_prices[data._name]
        
        # 开仓逻辑
        available_cash = self.broker.getcash()
        for stock_name, _ in target_stocks:
            data = self.getdatabyname(stock_name)
            if self.getposition(data).size == 0:
                # 计算购买数量
                max_position = self.broker.getvalue() * self.p.max_position_per_stock
                target_value = min(available_cash / (num_stocks - len(self.holding_days)), 
                                 max_position)
                if target_value > 0:
                    size = int(target_value / data.close[0])
                    if size > 0:
                        self.buy(data=data, size=size)
                        self.entry_prices[data._name] = data.close[0]
                        available_cash -= size * data.close[0]
    
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'买入 {order.data._name}, 价格: {order.executed.price:.2f}, '
                        f'数量: {order.executed.size}, 成本: {order.executed.value:.2f}, '
                        f'手续费: {order.executed.comm:.2f}')
            else:
                self.log(f'卖出 {order.data._name}, 价格: {order.executed.price:.2f}, '
                        f'数量: {order.executed.size}, 金额: {order.executed.value:.2f}, '
                        f'手续费: {order.executed.comm:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'订单失败 {order.data._name}: {order.getstatusname()}')
    
    def notify_trade(self, trade):
        if trade.isclosed:
            self.log(f'交易结束 {trade.data._name}, 毛利润: {trade.pnl:.2f}, '
                    f'净利润: {trade.pnlcomm:.2f}')
    
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print(f'{dt.isoformat()}, {txt}') 