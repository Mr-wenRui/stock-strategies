from typing import Dict, Any
import backtrader as bt
from .base_analyzer import BaseAnalyzer
from .registry import AnalyzerRegistry
from utils.logger import Logger

logger = Logger.get_logger(__name__)

@AnalyzerRegistry.register(
    name='sharpe',
    order=10,
    enabled=True,
    description='计算夏普比率，评估风险调整后收益'
)
class SharpeAnalyzer(BaseAnalyzer):
    """夏普比率分析器"""
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    
    def _analyze(self, strategy) -> Dict[str, Any]:
        analysis = strategy.analyzers.sharpe.get_analysis()
        return {
            'sharpe_ratio': getattr(analysis, 'sharperatio', 0)
        }
    
    def _print_results(self, results: Dict[str, Any]):
        """打印夏普比率分析结果"""
        logger.info("\n====== 夏普比率分析 ======")
        logger.info(f"夏普比率: {results.get('sharpe_ratio', 0):.2f}")

@AnalyzerRegistry.register(
    name='drawdown',
    order=20,
    enabled=True,
    description='计算最大回撤等回撤指标'
)
class DrawdownAnalyzer(BaseAnalyzer):
    """回撤分析器"""
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    
    def _analyze(self, strategy) -> Dict[str, Any]:
        analysis = strategy.analyzers.drawdown.get_analysis()
        return {
            'max_drawdown': getattr(analysis.get('max', {}), 'drawdown', 0)
        }
    
    def _print_results(self, results: Dict[str, Any]):
        """打印回撤分析结果"""
        logger.info("\n====== 回撤分析 ======")
        logger.info(f"最大回撤: {results.get('max_drawdown', 0):.2f}%")

@AnalyzerRegistry.register(
    name='trades',
    order=30,
    enabled=True,
    description='分析交易统计指标'
)
class TradeAnalyzer(BaseAnalyzer):
    """交易分析器"""
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    def _analyze(self, strategy) -> Dict[str, Any]:
        analysis = strategy.analyzers.trades.get_analysis()
        total_trades = analysis.get('total', {}).get('total', 0)
        won_trades = analysis.get('won', {}).get('total', 0)
        
        return {
            'trades': {
                'total': total_trades,
                'won': won_trades,
                'lost': analysis.get('lost', {}).get('total', 0),
                'win_rate': (won_trades / total_trades * 100) if total_trades > 0 else 0,
                'pnl_net': analysis.get('pnl', {}).get('net', {}).get('total', 0),
                'pnl_gross': analysis.get('pnl', {}).get('gross', {}).get('total', 0)
            }
        }
    
    def _print_results(self, results: Dict[str, Any]):
        """打印交易分析结果"""
        trades = results.get('trades', {})
        logger.info("\n====== 基础交易分析 ======")
        logger.info(f"总交易次数: {trades.get('total', 0)}")
        logger.info(f"盈利交易: {trades.get('won', 0)}")
        logger.info(f"亏损交易: {trades.get('lost', 0)}")
        logger.info(f"胜率: {trades.get('win_rate', 0):.2f}%")
        logger.info(f"净收益: {trades.get('pnl_net', 0):,.2f}")
        logger.info(f"总收益: {trades.get('pnl_gross', 0):,.2f}")

class SystemQualityAnalyzer(BaseAnalyzer):
    """
    系统质量分析器：计算策略的系统质量数（SQN）
    SQN用于评估交易系统的稳定性和可靠性
    """
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        """添加SQN分析器到cerebro"""
        cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    
    def _analyze(self, strategy) -> Dict[str, Any]:
        """
        计算系统质量数
        SQN = (平均收益/收益标准差) * sqrt(交易次数)
        """
        analysis = strategy.analyzers.sqn.get_analysis()
        return {
            'sqn': getattr(analysis, 'sqn', 0)
        } 