from strategies.base_strategy import BaseStrategy
import backtrader as bt

class ExampleStrategy(BaseStrategy):
    """示例策略：简单的双均线策略"""
    
    params = (
        ('fast_period', 10),  # 快速均线周期
        ('slow_period', 30),  # 慢速均线周期
    )

    def __init__(self):
        super(ExampleStrategy, self).__init__()
        
        # 计算技术指标
        self.fast_ma = {}
        self.slow_ma = {}
        self.crossover = {}
        
        # 为每个数据源计算指标
        for i, data in enumerate(self.datas):
            # 获取股票代码
            code = data._name
            # 计算快速和慢速均线
            self.fast_ma[code] = bt.indicators.SMA(data, period=self.p.fast_period)
            self.slow_ma[code] = bt.indicators.SMA(data, period=self.p.slow_period)
            # 计算交叉信号
            self.crossover[code] = bt.indicators.CrossOver(
                self.fast_ma[code],
                self.slow_ma[code]
            )

    def next(self):
        """策略逻辑实现"""
        # 遍历所有数据源
        for i, data in enumerate(self.datas):
            code = data._name
            
            # 获取当前持仓
            pos = self.get_position_size(code)
            
            # 金叉买入信号
            if self.crossover[code] > 0 and not pos:
                self.buy(data=data, size=self.p.size)
                self.log(f'{code} 金叉买入信号')
            
            # 死叉卖出信号
            elif self.crossover[code] < 0 and pos:
                self.sell(data=data, size=pos)
                self.log(f'{code} 死叉卖出信号')

if __name__ == '__main__':
    strategy = ExampleStrategy()
    strategy.run_backtest()
