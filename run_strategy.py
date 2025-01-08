from strategies.example_strategy import ExampleStrategy
from utils.log_config import LogConfig

def main():
    """运行回测"""
    # 设置日志配置
    LogConfig.setup_logging(
        log_level='DEBUG',
        log_dir='logs'
    )
    
    # 设置回测参数
    params = {
        'fast_period': 10,
        'slow_period': 30,
        'position_pct': 0.95
    }
    
    # 运行回测
    results = ExampleStrategy.run_backtest(
        codes=['000001', '000002'],
        start_date='2022-01-01',
        end_date='2024-12-31',
        init_cash=1000000,
        plot=True,
        debug=True,  # 启用调试模式以显示详细日志
        **params
    )
    
    if not results.get('success', False):
        print(f"回测失败: {results.get('error', '未知错误')}")

if __name__ == '__main__':
    main() 