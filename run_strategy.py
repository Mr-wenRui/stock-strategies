from strategies.example_strategy import ExampleStrategy
from utils.config import Config

if __name__ == '__main__':
    # 加载配置
    Config.load_config()
    
    # 运行回测
    results = ExampleStrategy.run_backtest(
        codes=['000001', '000002'],  # 可以是单个股票代码或列表
        start_date='2021-01-01',
        end_date='2024-01-01',
        init_cash=1000000,
        plot=True,
        # 策略参数
        fast_period=10,
        slow_period=30,
        debug=True
    )
    
    # 检查结果
    if results.get('success', False):
        print(f"回测成功完成！")
        print(f"最终资金: {results['final_value']:,.2f}")
        print(f"收益率: {results['returns']:.2f}%")
        print(f"夏普比率: {results['sharpe_ratio']:.2f}")
    else:
        print(f"回测失败: {results.get('error', '未知错误')}") 