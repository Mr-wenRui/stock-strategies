from datetime import datetime
import backtrader as bt

import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Any, Union, Type

from utils.logger import Logger

from .analyzers.analyzer_chain import AnalyzerChainBuilder
from .analyzers.registry import AnalyzerRegistry
from .observers.observer_builder import ObserverBuilder

from .data_loader.default_loader import DefaultDataLoader
from .data_loader.base_loader import BaseDataLoader
from .output.output_manager import OutputManager
from .notifications.notification_manager import NotificationManager
from .notifications.record_manager import RecordManager
from .output.console_observer import ConsoleObserver
from .output.result_collector import ResultCollector
from .observers.base_observer import BaseObserver

logger = Logger.get_logger(__name__)

class BaseStrategy(bt.Strategy):
    """
    交易策略基类
    提供基础的策略框架和通用功能，包括：
    1. 数据管理：加载和维护交易数据
    2. 订单管理：跟踪订单状态和执行情况
    3. 仓位管理：监控持仓状态和变化
    4. 性能分析：计算和记录交易表现
    5. 风险控制：实现基本的风险管理功能
    
    使用方法：
    1. 继承此类创建具体策略
    2. 重写 next() 方法实现交易逻辑
    3. 使用 run_backtest() 运行回测
    
    示例：
        class MyStrategy(BaseStrategy):
            def next(self):
                if self.should_buy():
                    self.buy()
                elif self.should_sell():
                    self.sell()
    """
    
    # 策略参数配置
    params = (
        ('commission', 0.0003),     # 手续费率（默认0.03%）
        ('slip_percentage', 0.001), # 滑点率（默认0.1%）
        ('init_cash', 1000000),    # 初始资金（默认100万）
        ('size', 100),             # 每手交易数量（默认100股）
        ('debug', False),          # 调试模式开关
    )

    def __init__(self):
        """
        策略初始化
        完成以下工作：
        1. 初始化性能统计指标
        2. 设置订单和持仓跟踪器
        3. 建立数据索引映射
        4. 加载必要的数据
        5. 配置交易成本（滑点和手续费）
        """
        super(BaseStrategy, self).__init__()
        
        # 测试日志系统
        logger.debug("策略初始化开始")
        
        # 性能统计指标
        self.order_stats = {
            'total': 0,
            'won': 0,
            'lost': 0,
        }
        
        # 订单和持仓管理
        self.orders = {}
        self.position_tracker = {}
        
        # 数据索引映射
        self.data_map = {d._name: i for i, d in enumerate(self.datas)}
        
        # 设置交易成本
        self._setup_trading_costs()
        
        # 设置通知管理器
        NotificationManager.set_strategy(self)
        
        # 添加输出观察者
        OutputManager.add_observer(ConsoleObserver())
        
        logger.debug("策略初始化完成")

    def _setup_trading_costs(self):
        """配置交易成本"""
        self.broker.set_slippage_perc(self.p.slip_percentage)
        self.broker.addcommissioninfo(
            bt.CommInfoBase(
                commission=self.p.commission,
                mult=1.0,
                margin=None,
                commtype=bt.CommInfoBase.COMM_PERC,
                percabs=True,
                stocklike=True,
            )
        )
        self.broker.set_cash(self.p.init_cash)

    def notify_order(self, order):
        """订单状态更新通知"""
        NotificationManager.notify_order(order)

    def notify_trade(self, trade):
        """交易完成通知"""
        NotificationManager.notify_trade(trade)

    def get_position_size(self, code: str) -> int:
        """获取指定股票的持仓数量"""
        try:
            data_idx = self.data_map.get(code)
            if data_idx is None:
                logger.warning(f"未找到股票 {code} 的数据")
                return 0
            
            position = self.getposition(self.datas[data_idx])
            return position.size if position else 0
        
        except Exception as e:
            logger.error(f"获取持仓数量失败: {str(e)}")
            return 0

    def log(self, txt: str, dt: datetime = None):
        """输出日志信息"""
        if self.p.debug:
            dt = dt or self.datas[0].datetime.date(0)
            logger.info(f'{dt}: {txt}')

    def next(self):
        """策略主逻辑"""
        if self._check_account_status():
            self._next()
        else:
            self._close_all_positions()

    def _check_account_status(self) -> bool:
        """检查账户状态"""
        try:
            portfolio_value = self.broker.getvalue()
            init_cash = self.broker.startingcash
            
            drawdown = (init_cash - portfolio_value) / init_cash * 100
            
            if drawdown >= 50:
                self.log(f"触发最大回撤停损: {drawdown:.2f}%")
                return False
            
            if portfolio_value <= init_cash * 0.1:
                self.log(f"触发资金量停损: {portfolio_value:,.2f}")
                return False
            
            if self.broker.getcash() < 1000:
                self.log("现金不足，停止交易")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"检查账户状态失败: {str(e)}")
            return False

    def _close_all_positions(self):
        """清空所有持仓"""
        try:
            for data in self.datas:
                position = self.getposition(data)
                if position.size != 0:
                    self.close(data=data)
                    self.log(f"清仓 {data._name}: {position.size} 股")
        except Exception as e:
            self.log(f"清仓失败: {str(e)}")

    def _next(self):
        """子类实现的交易逻辑"""
        raise NotImplementedError("子类必须实现 _next() 方法")

    @classmethod
    def run_backtest(cls, codes: Union[str, List[str]], start_date: str, end_date: str,
                    init_cash: float = 1000000, plot: bool = True,
                    analyzers: Dict[str, bool] = None, 
                    observers: Dict[str, bool] = None,
                    data_loader: BaseDataLoader = None,
                    **kwargs) -> Dict[str, Any]:
        """运行回测"""
        try:
            # 重置记录管理器
            RecordManager.get_instance().reset()
            
            # 创建回测引擎
            cerebro = bt.Cerebro()
            
            # 2. 设置回测参数
            cerebro.broker.setcash(init_cash)
            cerebro.tradehistory = True
            
            # 3. 配置分析器和观察者
            AnalyzerRegistry.setup_analyzers(analyzers)
            AnalyzerChainBuilder.add_analyzers(cerebro)
            
            # 设置观察者
            observers = ObserverBuilder.setup_observers(cerebro, observers)
            # 添加默认的 Backtrader 观察者
            cerebro.addobserver(bt.observers.Broker)
            cerebro.addobserver(bt.observers.Trades)
            cerebro.addobserver(bt.observers.BuySell)
            
            # 4. 加载数据
            data_loader = data_loader or DefaultDataLoader()
            data_loader.load_data(debug=kwargs.get('debug', False))
            data_loader.create_data_feeds(codes, start_date, end_date, cerebro)
            
            # 5. 添加策略
            cerebro.addstrategy(cls, **kwargs)
            
            # 6. 运行回测
            results = cerebro.run()
            
            # 7. 绘制结果
            if plot:
                # 设置绘图样式
                plt.style.use('classic')  # 使用经典样式
                
                # 设置中文字体
                plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
                plt.rcParams['axes.unicode_minus'] = False    # 用来正常显示负号
                
                # 设置图表样式
                plt.rcParams.update({
                    'figure.figsize': [20, 12],
                    'figure.dpi': 100,
                    'axes.grid': True,
                    'grid.linestyle': '--',
                    'grid.alpha': 0.5,
                    'axes.linewidth': 1.5,
                    'axes.labelsize': 12,
                    'xtick.labelsize': 10,
                    'ytick.labelsize': 10,
                    'legend.fontsize': 10,
                    'lines.linewidth': 1.5,
                })
                
                # 绘制回测结果
                figs = cerebro.plot(
                    style='candle',           # 使用K线图
                    barup='red',              # 上涨为红色
                    bardown='green',          # 下跌为绿色
                    volup='red',              # 成交量上涨为红色
                    voldown='green',          # 成交量下跌为绿色
                    grid=True,                # 显示网格
                    volume=True,              # 显示成交量
                    fmt_x_ticks='%Y-%m-%d',   # 日期格式
                    **kwargs
                )
                
                # 调整图表布局
                for fig in figs:
                    plt.tight_layout()  # 自动调整布局
            
            # 8. 处理结果
            if results and len(results) > 0:
                strategy = results[0]
                # 使用结果收集器收集数据
                final_results = ResultCollector.collect_results(
                    strategy=strategy,
                    cerebro=cerebro,
                    init_cash=init_cash
                )
                
                # 输出结果
                OutputManager.output_results(final_results)
                
                return final_results
            
            return {
                'success': False,
                'error': "回测未返回结果"
            }
            
        except Exception as e:
            error_msg = f"回测执行过程中发生错误: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def notify_cashvalue(self, cash, value):
        """现金变动通知"""
        logger.info(f"现金变动: 当前现金={cash:,.2f}, 总资产={value:,.2f}")
        NotificationManager.notify_cash(cash)

    def notify_store(self, msg, *args, **kwargs):
        """数据源通知"""
        logger.info(f"数据源通知: {msg}")
        NotificationManager.notify_store(msg)

    def get_observer_data(self, observer_type: Type[BaseObserver], line_name: str) -> List[float]:
        """获取观察者数据"""
        try:
            # 查找指定类型的观察者
            observer = [obs for obs in self.observers if isinstance(obs, observer_type)]
            if not observer:
                return []
            
            # 获取观察者数据
            observer_data = observer[0].get_series()
            return observer_data.get(line_name, [])
            
        except Exception as e:
            logger.error(f"获取观察者数据失败: {str(e)}")
            return []

    def get_latest_observer_value(self, observer_type: Type[BaseObserver], line_name: str) -> float:
        """获取观察者最新值"""
        try:
            # 查找指定类型的观察者
            observer = [obs for obs in self.observers if isinstance(obs, observer_type)]
            if not observer:
                return 0.0
            
            # 获取最新值
            last_values = observer[0].get_last_values()
            return last_values.get(line_name, 0.0)
            
        except Exception as e:
            logger.error(f"获取观察者最新值失败: {str(e)}")
            return 0.0

    def get_observer_analysis(self, observer_type: Type[BaseObserver]) -> Dict[str, Any]:
        """获取观察者分析结果"""
        try:
            # 查找指定类型的观察者
            observer = [obs for obs in self.observers if isinstance(obs, observer_type)]
            if not observer:
                return {}
            
            # 获取分析结果
            return observer[0].get_analysis()
            
        except Exception as e:
            logger.error(f"获取观察者分析结果失败: {str(e)}")
            return {}

