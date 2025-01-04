from datetime import datetime
import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Any, Union
from utils.redis_helper import RedisHelper
from utils.clickhouse_helper import ClickHouseClient
from utils.logger import Logger
import numpy as np
from .analyzers.analyzer_chain import AnalyzerChainBuilder
from .analyzers.registry import AnalyzerRegistry

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
        
        # 性能统计指标
        self.order_stats = {
            'total': 0,  # 总交易次数
            'won': 0,    # 盈利交易次数
            'lost': 0,   # 亏损交易次数
        }
        
        # 订单和持仓管理
        self.orders = {}          # 未完成订单跟踪器 {order_ref: order}
        self.position_tracker = {} # 持仓跟踪器 {symbol: position}
        
        # 数据索引映射（用于快速查找数据）
        self.data_map = {d._name: i for i, d in enumerate(self.datas)}
        
        # 加载策略所需数据
        self._load_data()
        
        # 设置交易成本
        self._setup_trading_costs()

    def _setup_trading_costs(self):
        """
        配置交易成本
        包括：
        1. 设置滑点模型
        2. 设置佣金模型
        3. 设置初始资金
        """
        # 设置滑点
        self.broker.set_slippage_perc(self.p.slip_percentage)
        
        # 设置佣金模型
        self.broker.addcommissioninfo(
            bt.CommInfoBase(
                commission=self.p.commission,    # 佣金费率
                mult=1.0,                        # 乘数（股票为1）
                margin=None,                     # 保证金（现货交易为None）
                commtype=bt.CommInfoBase.COMM_PERC,  # 按百分比收取
                percabs=True,                    # commission已经是百分比
                stocklike=True,                  # 股票类型资产
            )
        )
        
        # 设置初始资金
        self.broker.set_cash(self.p.init_cash)

    def _load_data(self):
        """
        加载策略运行所需的数据
        包括：
        1. 股票基本信息
        2. 交易日历
        3. 实时行情数据
        
        数据来源：
        - Redis缓存
        - ClickHouse数据库
        """
        try:
            # 加载股票基本信息
            self.stock_info = RedisHelper.get_df('stock:basic')
            
            # 加载交易日历
            calendar_df = RedisHelper.get_df('stock:calendar')
            self.trade_calendar = calendar_df['trade_date'].tolist() if not calendar_df.empty else []
            
            # 加载最新行情数据
            self.latest_quotes = RedisHelper.get_df('stock:realtime')
            
            # 记录数据加载时间
            self.data_load_time = datetime.now()
            
            # 调试模式下打印数据加载信息
            if self.p.debug:
                self._log_data_info()
            
        except Exception as e:
            logger.error(f"加载策略数据失败: {str(e)}")
            raise

    def _log_data_info(self):
        """打印数据加载信息"""
        logger.info("策略数据加载完成")
        logger.info(f"加载了 {len(self.trade_calendar)} 个交易日")
        logger.info(f"加载了 {len(self.stock_info)} 只股票的基本信息")
        logger.info(f"加载了 {len(self.latest_quotes)} 只股票的实时行情")

    def notify_order(self, order):
        """
        订单状态更新通知
        处理订单的各种状态变化：
        1. 订单提交和接受
        2. 订单完成（成功/失败）
        3. 更新交易统计
        4. 清理已完成订单
        
        参数:
            order: backtrader的Order对象
        """
        if order.status in [order.Submitted, order.Accepted]:
            # 订单已提交或已接受，等待执行
            return

        if order.status in [order.Completed]:
            # 订单完成
            self._handle_completed_order(order)
                
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            # 订单失败
            self.log(f'订单失败: {order.status}')
        
        # 清理已完成订单
        self.orders.pop(order.ref, None)

    def _handle_completed_order(self, order):
        """处理已完成的订单"""
        # 获取订单信息
        trade_info = {
            'datetime': order.executed.dt,
            'type': 'BUY' if order.isbuy() else 'SELL',
            'size': order.executed.size,
            'price': order.executed.price,
            'value': order.executed.value,
            'commission': order.executed.comm,
        }
        
        # 计算收益
        if hasattr(order.executed, 'pnl'):
            trade_info['pnl'] = order.executed.pnl
        else:
            # 如果没有pnl属性，手动计算
            if order.isbuy():
                trade_info['pnl'] = 0  # 买入时收益为0
            else:
                # 卖出时计算收益
                position = self.getposition(order.data)
                if position:
                    trade_info['pnl'] = (order.executed.price - position.price) * order.executed.size
                else:
                    trade_info['pnl'] = 0
        
        # 计算净收益（减去手续费）
        trade_info['pnlcomm'] = trade_info['pnl'] - trade_info['commission']
        
        # 记录交易详情
        if not hasattr(self, 'trades_history'):
            self.trades_history = []
        self.trades_history.append(trade_info)
        
        # 更新交易统计
        self.order_stats['total'] += 1
        if trade_info['pnlcomm'] > 0:
            self.order_stats['won'] += 1
        else:
            self.order_stats['lost'] += 1
        
        # 打印交易信息
        self._log_trade(trade_info)
    
    def _log_trade(self, trade_info: Dict[str, Any]):
        """打印交易信息"""
        action = "买入" if trade_info['type'] == 'BUY' else "卖出"
        msg = (
            f"{action}执行: "
            f"数量={trade_info['size']}, "
            f"价格={trade_info['price']:.2f}, "
            f"金额={trade_info['value']:.2f}, "
            f"手续费={trade_info['commission']:.2f}"
        )
        
        # 如果是卖出交易，添加收益信息
        if trade_info['type'] == 'SELL':
            msg += f", 净收益={trade_info['pnlcomm']:.2f}"
        
        logger.info(msg)

    def notify_trade(self, trade):
        """
        交易完成通知
        在交易结束时记录盈亏情况
        
        参数:
            trade: backtrader的Trade对象
        """
        if not trade.isclosed:
            return
        
        # 更新交易统计
        pnl = trade.pnl if hasattr(trade, 'pnl') else 0
        pnlcomm = trade.pnlcomm if hasattr(trade, 'pnlcomm') else (pnl - trade.commission)
        
        self.log(f'交易结束: 毛利润 {pnl:.2f}, 净利润 {pnlcomm:.2f}')

    def get_position_size(self, code: str) -> int:
        """
        获取指定股票的持仓数量
        
        参数:
            code: 股票代码
            
        返回:
            持仓数量（股）
        """
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
        """
        输出日志信息
        
        参数:
            txt: 日志内容
            dt: 时间戳（默认使用当前bar的时间）
        """
        if self.p.debug:
            dt = dt or self.datas[0].datetime.date(0)
            logger.info(f'{dt}: {txt}')

    @classmethod
    def run_backtest(cls, codes: Union[str, List[str]], start_date: str, end_date: str,
                    init_cash: float = 1000000, plot: bool = True,
                    analyzers: Dict[str, bool] = None, **kwargs) -> Dict[str, Any]:
        """运行回测"""
        try:
            # 1. 配置分析器
            analyzers = cls._setup_analyzers(analyzers)
            
            # 2. 创建回测引擎
            cerebro = cls._create_cerebro(init_cash)
            
            # 3. 加载数据
            data_result = cls._load_data_manager(cerebro, 
                                               codes if isinstance(codes, list) else [codes], 
                                               start_date, 
                                               end_date)
            if not data_result['success']:
                return {'error': data_result['error'], 'success': False}
            
            if data_result['loaded_data'] == 0:
                return {'error': "没有成功加载任何数据", 'success': False}
            
            # 4. 添加策略
            cerebro.addstrategy(cls, **kwargs)
            
            # 5. 添加分析器
            analyzer_chain = AnalyzerChainBuilder.add_analyzers(cerebro)
            
            # 6. 运行回测
            logger.info(f"开始回测 - 初始资金: {init_cash:,.2f}")
            results = cerebro.run()
            
            # 7. 处理结果
            return cls._process_results(results[0], cerebro, analyzer_chain, init_cash, plot)
            
        except Exception as e:
            error_msg = f"回测执行过程中发生错误: {str(e)}"
            logger.error(error_msg)
            return {'error': error_msg, 'success': False}

    @classmethod
    def _setup_analyzers(cls, analyzers: Dict[str, bool] = None) -> Dict[str, bool]:
        """配置分析器"""
        if analyzers is None:
            analyzers = {
                # 基础分析器
                'sharpe': True,
                'drawdown': True,
                'trades': True,
                # 高级分析器
                'returns': True,
                'risk': True,
                'trade_stats': True,
                'position': True
            }
        
        # 更新分析器状态
        for name, enabled in analyzers.items():
            if enabled:
                AnalyzerRegistry.enable(name)
            else:
                AnalyzerRegistry.disable(name)
        
        return analyzers

    @classmethod
    def _create_cerebro(cls, init_cash: float) -> bt.Cerebro:
        """创建回测引擎"""
        cerebro = bt.Cerebro()
        cerebro.broker.set_cash(init_cash)
        return cerebro

    @classmethod
    def _load_data_manager(cls, cerebro: bt.Cerebro, codes: List[str], 
                          start_date: str, end_date: str) -> Dict[str, Any]:
        """
        统一管理数据加载
        包括：股票数据和其他辅助数据
        """
        result = {
            'success': True,
            'loaded_data': 0,
            'error': None
        }
        
        try:
            # 加载股票数据
            for code in codes:
                df = cls._load_stock_data(code, start_date, end_date)
                if df.empty:
                    logger.warning(f"股票 {code} 数据为空，跳过")
                    continue
                    
                data = cls._create_data_feed(df, start_date, end_date, name=code)
                cerebro.adddata(data)
                result['loaded_data'] += 1
                logger.info(f"成功加载股票 {code} 的数据")
            
            # 加载其他必要数据（如行业数据等）
            cls._load_auxiliary_data(start_date, end_date)
            
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
            logger.error(f"数据加载失败: {str(e)}")
            
        return result
    
    @staticmethod
    def _create_data_feed(df: pd.DataFrame, start_date: str, end_date: str, 
                         name: str = None, plot: bool = True) -> bt.feeds.PandasData:
        """创建数据源对象"""
        return bt.feeds.PandasData(
            dataname=df,
            datetime='trade_date',
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1,
            fromdate=pd.to_datetime(start_date),
            todate=pd.to_datetime(end_date),
            name=name,
            plot=plot
        )
    
    @staticmethod
    def _load_stock_data(code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从数据库加载股票数据"""
        query = """
        SELECT 
            trade_date,
            open,
            high,
            low,
            close,
            volume,
            amount
        FROM stock_daily 
        WHERE stock_code = %(code)s 
        AND trade_date BETWEEN %(start_date)s AND %(end_date)s
        ORDER BY trade_date
        """
        params = {'code': code, 'start_date': start_date, 'end_date': end_date}
        df = ClickHouseClient.query_df(query, params)
        
        if not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        return df
    
    @staticmethod
    def _load_index_data(code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从数据库加载指数数据"""
        query = """
        SELECT 
            trade_date,
            open,
            high,
            low,
            close,
            volume,
            amount
        FROM index_daily 
        WHERE index_code = %(code)s 
        AND trade_date BETWEEN %(start_date)s AND %(end_date)s
        ORDER BY trade_date
        """
        params = {'code': code, 'start_date': start_date, 'end_date': end_date}
        df = ClickHouseClient.query_df(query, params)
        
        if not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        return df

    @staticmethod
    def _print_results(results: Dict[str, Any]):
        """打印回测结果"""
        try:
            if not results.get('success', False):
                logger.error(f"回测失败: {results.get('error', '未知错误')}")
                return

            # 基本信息
            logger.info("\n====== 回测基本信息 ======")
            logger.info(f"期末资金: {results['final_value']:,.2f}")
            logger.info(f"总收益率: {results['returns']:.2f}%")
            
            # 其他分析结果由各个分析器自己负责打印
            
        except Exception as e:
            logger.error(f"打印回测结果时发生错误: {str(e)}")

    @classmethod
    def _load_auxiliary_data(cls, start_date: str, end_date: str) -> None:
        """
        加载辅助数据（如行业数据、指数数据等）
        子类可以重写此方法以加载额外的数据
        """
        pass  # 基类中为空实现，子类可以根据需要重写

    @classmethod
    def _process_results(cls, strategy, cerebro: bt.Cerebro, 
                        analyzer_chain, init_cash: float, 
                        plot: bool) -> Dict[str, Any]:
        """处理回测结果"""
        try:
            # 获取回测结果
            portfolio_value = cerebro.broker.getvalue()
            returns = (portfolio_value / init_cash - 1) * 100

            # 获取分析结果
            analysis_results = AnalyzerChainBuilder.get_analysis_results(
                strategy, analyzer_chain)
            
            # 合并结果
            final_results = {
                'success': True,
                'final_value': portfolio_value,
                'returns': returns,
                **analysis_results
            }

            # 输出结果
            cls._print_results(final_results)

            # 绘制图表
            if plot:
                plot_results(cerebro, portfolio_value, init_cash)

            return final_results
            
        except Exception as e:
            error_msg = f"处理回测结果时发生错误: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

def plot_results(cerebro, portfolio_value: float, init_cash: float):
    """绘制回测结果图表"""
    try:
        # 设置图表样式
        plt.style.use('seaborn-v0_8-darkgrid')
        
        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig = plt.figure(figsize=(16, 9))
        
        # 设置网格布局
        gs = fig.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.3)
        
        # 绘制主图（K线和交易）
        ax1 = fig.add_subplot(gs[0])
        cerebro.plot(style='candlestick',
                    barup='red',     # 上涨蜡烛颜色
                    bardown='green', # 下跌蜡烛颜色
                    volup='red',     # 上涨成交量颜色
                    voldown='green', # 下跌成交量颜色
                    grid=True,       # 显示网格
                    volume=True,     # 显示成交量
                    ax=ax1)[0][0]
        
        ax1.set_title('交易策略回测结果', fontsize=12, pad=15)
        ax1.legend(['价格', '买入', '卖出'], loc='upper left')
        
        # 绘制收益曲线
        ax2 = fig.add_subplot(gs[1])
        
        # 计算收益率
        current_drawdown = (portfolio_value - init_cash) / init_cash * 100
        ax2.plot([0, 1], [0, current_drawdown], color='blue', linewidth=1.5)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        if current_drawdown >= 0:
            ax2.fill_between([0, 1], [0, current_drawdown], 0, color='red', alpha=0.3)
        else:
            ax2.fill_between([0, 1], [0, current_drawdown], 0, color='green', alpha=0.3)
            
        ax2.set_title(f'收益率曲线 (总收益率: {current_drawdown:.2f}%)', 
                     fontsize=10)
        ax2.grid(True)
        
        # 添加总体信息
        returns_pct = (portfolio_value / init_cash - 1) * 100
        fig.suptitle(f'策略回测分析\n' 
                    f'初始资金: {init_cash:,.0f}  期末资金: {portfolio_value:,.0f}  '
                    f'总收益率: {returns_pct:.2f}%',
                    fontsize=14, y=0.95)
        
        # 调整布局
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        logger.error(f"绘图失败: {str(e)}") 