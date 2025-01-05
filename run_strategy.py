from strategies.example_strategy import ExampleStrategy

def main():
    """运行回测"""
    # 设置回测参数
    params = {
        'fast_period': 10,
        'slow_period': 30,
        'position_pct': 0.95
    }
    
    # 运行回测
    results = ExampleStrategy.run_backtest(  # 使用类方法运行回测
        codes=['000001', '000002'],  # 回测的股票代码
        start_date='2022-01-01',           # 回测开始日期
        end_date='2024-12-31',             # 回测结束日期
        init_cash=1000000,                 # 初始资金
        plot=True,                         # 是否显示图表
        **params                           # 策略参数
    )
    
    # 检查结果
    if results.get('success', False):
        print(f"回测成功完成！")
        print(f"最终资金: {results['final_value']:,.2f}")
        print(f"收益率: {results['returns']:.2f}%")
        
        # 打印观察者数据
        if observer_data := results.get('observer_data'):
            # 风险指标
            if risk_data := observer_data.get('risk_metrics'):
                if volatility := risk_data.get('volatility'):
                    print(f"最终波动率: {volatility[-1]:.2f}%")
                if drawdown := risk_data.get('drawdown'):
                    print(f"最大回撤: {max(drawdown):.2f}%")
            
            # 交易指标
            if trade_data := observer_data.get('trade_metrics'):
                if win_rate := trade_data.get('win_rate'):
                    print(f"最终胜率: {win_rate[-1]:.2f}%")
                if profit_factor := trade_data.get('profit_factor'):
                    print(f"最终盈亏比: {profit_factor[-1]:.2f}")
    else:
        print(f"回测失败: {results.get('error', '未知错误')}")

if __name__ == '__main__':
    main() 