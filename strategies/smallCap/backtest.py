import backtrader as bt
from datetime import datetime, timedelta
from strategies.smallCap.strategy import SmallCapStrategy
from strategies.smallCap.data_loader import DataLoader
from utils.context import context

class BackTest:
    def __init__(self, initial_cash=1000000.0):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(initial_cash)
        self.cerebro.broker.setcommission(commission=0.0003)  # 设置手续费为万三
        self.data_loader = DataLoader()
        
    def prepare_data(self, start_date, end_date, min_listing_days=250):
        """准备回测数据"""
        # 获取符合条件的股票列表
        stock_list = self.data_loader.filter_stocks(
            min_listing_days=min_listing_days,
            exclude_st=True
        )
        
        # 获取历史数据
        df = self.data_loader.get_history_data(stock_list, start_date, end_date)
        
        # 将数据按股票代码分组并添加到cerebro
        for code in stock_list:
            stock_df = df[df['code'] == code].copy()
            if len(stock_df) > 0:
                stock_df.set_index('trade_date', inplace=True)
                data = bt.feeds.PandasData(
                    dataname=stock_df,
                    datetime=None,  # 使用索引作为日期
                    open='open',
                    high='high',
                    low='low',
                    close='close',
                    volume='volume',
                    openinterest=-1,  # 不使用持仓量
                    
                    # 添加自定义数据列
                    market_cap='market_cap',
                    turnover_rate='turnover_rate',
                    amount='amount',
                    pct_change='pct_change'
                )
                self.cerebro.adddata(data, name=code)
    
    def run(self, start_date, end_date):
        """运行回测"""
        # 准备数据
        self.prepare_data(start_date, end_date)
        
        # 添加策略
        self.cerebro.addstrategy(SmallCapStrategy)
        
        # 添加分析器
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # 运行回测
        print(f'初始资金: {self.cerebro.broker.getvalue():.2f}')
        results = self.cerebro.run()
        strat = results[0]
        
        # 输出回测结果
        self._print_results(strat)
        
        # 绘制回测结果
        self.cerebro.plot(style='candlestick')
        
    def _print_results(self, strat):
        """打印回测结果"""
        print(f'最终资金: {self.cerebro.broker.getvalue():.2f}')
        print(f'总收益率: {(self.cerebro.broker.getvalue() / self.cerebro.broker.startingcash - 1) * 100:.2f}%')
        print(f'夏普比率: {strat.analyzers.sharpe.get_analysis()["sharperatio"]:.2f}')
        print(f'最大回撤: {strat.analyzers.drawdown.get_analysis()["max"]["drawdown"]:.2f}%')
        print(f'年化收益率: {strat.analyzers.returns.get_analysis()["rnorm100"]:.2f}%')
        
        trades = strat.analyzers.trades.get_analysis()
        print(f'\n交易统计:')
        print(f'总交易次数: {trades.total.total}')
        if trades.total.total > 0:
            print(f'盈利交易: {trades.won.total}')
            print(f'亏损交易: {trades.lost.total}')
            print(f'胜率: {trades.won.total / trades.total.total * 100:.2f}%')
            if trades.won.total > 0:
                print(f'平均盈利: {trades.won.pnl.average:.2f}')
                print(f'最大盈利: {trades.won.pnl.max:.2f}')
            if trades.lost.total > 0:
                print(f'平均亏损: {trades.lost.pnl.average:.2f}')
                print(f'最大亏损: {trades.lost.pnl.max:.2f}')

if __name__ == '__main__':
    context.init_config()
    # 运行回测
    backtest = BackTest(initial_cash=1000000.0)
    backtest.run(
        start_date='2020-01-01',
        end_date='2023-12-31'
    ) 