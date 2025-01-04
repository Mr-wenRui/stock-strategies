from typing import Dict, Any
import numpy as np
import backtrader as bt
from .base_analyzer import BaseAnalyzer
from .registry import AnalyzerRegistry
from utils.logger import Logger

logger = Logger.get_logger(__name__)

@AnalyzerRegistry.register(
    name='returns',
    order=15,
    enabled=True,
    description='计算各类收益率指标：年化收益、月度收益等'
)
class ReturnsAnalyzer(BaseAnalyzer):
    """收益率分析器"""
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='time_return')
        cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='annual_return')
        
    def _analyze(self, strategy) -> Dict[str, Any]:
        time_analysis = strategy.analyzers.time_return.get_analysis()
        annual_analysis = strategy.analyzers.annual_return.get_analysis()
        
        # 计算月度收益率
        returns = list(time_analysis.values())
        monthly_returns = []
        
        if returns:
            # 将日收益率转换为月度收益率
            returns_array = np.array(returns)
            # 假设平均每月21个交易日，但处理不完整月份
            n_months = len(returns) // 21
            if n_months > 0:
                # 完整月份的收益率
                full_months = returns_array[:n_months * 21].reshape(n_months, 21)
                monthly_returns = (1 + full_months).prod(axis=1) - 1
                
                # 处理剩余的交易日
                remaining_days = len(returns) % 21
                if remaining_days > 0:
                    last_month = returns_array[n_months * 21:]
                    last_month_return = (1 + last_month).prod() - 1
                    monthly_returns = np.append(monthly_returns, last_month_return)
        
        # 计算年化收益率
        annual_return = np.mean(list(annual_analysis.values())) if annual_analysis else 0
        
        return {
            'returns_metrics': {
                'annual_return': float(annual_return * 100),  # 转换为百分比
                'monthly_returns': monthly_returns.tolist() if len(monthly_returns) > 0 else [],
                'best_month': float(np.max(monthly_returns) * 100) if len(monthly_returns) > 0 else 0,
                'worst_month': float(np.min(monthly_returns) * 100) if len(monthly_returns) > 0 else 0,
                'avg_monthly_return': float(np.mean(monthly_returns) * 100) if len(monthly_returns) > 0 else 0
            }
        }
    
    def _print_results(self, results: Dict[str, Any]):
        """打印收益率分析结果"""
        metrics = results.get('returns_metrics', {})
        logger.info("\n====== 收益率分析 ======")
        logger.info(f"年化收益率: {metrics.get('annual_return', 0):.2f}%")
        logger.info(f"平均月度收益: {metrics.get('avg_monthly_return', 0):.2f}%")
        logger.info(f"最佳月度收益: {metrics.get('best_month', 0):.2f}%")
        logger.info(f"最差月度收益: {metrics.get('worst_month', 0):.2f}%")

@AnalyzerRegistry.register(
    name='risk',
    order=25,
    enabled=True,
    description='计算风险相关指标：波动率、Beta、最大回撤持续期等'
)
class RiskAnalyzer(BaseAnalyzer):
    """风险分析器"""
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='returns')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        
    def _analyze(self, strategy) -> Dict[str, Any]:
        returns = list(strategy.analyzers.returns.get_analysis().values())
        drawdown = strategy.analyzers.drawdown.get_analysis()
        
        # 计算风险指标
        returns_array = np.array(returns) if returns else np.array([0])
        volatility = np.std(returns_array) * np.sqrt(252)  # 年化波动率
        
        # 计算下行波动率
        downside_returns = returns_array[returns_array < 0]
        downside_vol = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
        
        return {
            'risk_metrics': {
                'volatility': float(volatility),
                'downside_volatility': float(downside_vol),
                'max_drawdown': getattr(drawdown.get('max', {}), 'drawdown', 0),
                'max_drawdown_duration': getattr(drawdown.get('max', {}), 'len', 0),
                'avg_drawdown': getattr(drawdown.get('average', {}), 'drawdown', 0),
                'avg_drawdown_duration': getattr(drawdown.get('average', {}), 'len', 0),
            }
        }
    
    def _print_results(self, results: Dict[str, Any]):
        """打印风险分析结果"""
        metrics = results.get('risk_metrics', {})
        logger.info("\n====== 风险分析 ======")
        logger.info(f"年化波动率: {metrics.get('volatility', 0):.2f}%")
        logger.info(f"下行波动率: {metrics.get('downside_volatility', 0):.2f}%")
        logger.info(f"最大回撤: {metrics.get('max_drawdown', 0):.2f}%")
        logger.info(f"最大回撤持续期: {metrics.get('max_drawdown_duration', 0)}天")
        logger.info(f"平均回撤: {metrics.get('avg_drawdown', 0):.2f}%")
        logger.info(f"平均回撤持续期: {metrics.get('avg_drawdown_duration', 0)}天")

@AnalyzerRegistry.register(
    name='trade_stats',
    order=35,
    enabled=True,
    description='计算详细的交易统计指标'
)
class TradeStatsAnalyzer(BaseAnalyzer):
    """交易统计分析器"""
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_stats')
        
    def _analyze(self, strategy) -> Dict[str, Any]:
        analysis = strategy.analyzers.trade_stats.get_analysis()
        
        # 获取交易统计
        total = analysis.get('total', {}).get('total', 0)
        won = analysis.get('won', {}).get('total', 0)
        lost = analysis.get('lost', {}).get('total', 0)
        
        # 计算盈亏统计
        pnl = analysis.get('pnl', {})
        gross = pnl.get('gross', {})
        net = pnl.get('net', {})
        
        # 计算平均持仓时间
        length = analysis.get('len', {})
        avg_bars = length.get('average', 0)
        
        return {
            'trade_statistics': {
                'total_trades': total,
                'won_trades': won,
                'lost_trades': lost,
                'win_rate': (won / total * 100) if total > 0 else 0,
                'profit_factor': abs(gross.get('won', 0) / gross.get('lost', 1)),
                'avg_trade': net.get('average', 0),
                'avg_win': analysis.get('won', {}).get('pnl', {}).get('average', 0),
                'avg_loss': analysis.get('lost', {}).get('pnl', {}).get('average', 0),
                'largest_win': analysis.get('won', {}).get('pnl', {}).get('max', 0),
                'largest_loss': analysis.get('lost', {}).get('pnl', {}).get('max', 0),
                'avg_bars_held': avg_bars,
                'total_net_profit': net.get('total', 0),
                'total_gross_profit': gross.get('total', 0),
            }
        }
    
    def _print_results(self, results: Dict[str, Any]):
        """打印交易统计结果"""
        stats = results.get('trade_statistics', {})
        logger.info("\n====== 交易统计 ======")
        logger.info(f"总交易次数: {stats.get('total_trades', 0)}")
        logger.info(f"盈利交易: {stats.get('won_trades', 0)}")
        logger.info(f"亏损交易: {stats.get('lost_trades', 0)}")
        logger.info(f"胜率: {stats.get('win_rate', 0):.2f}%")
        logger.info(f"盈亏比: {stats.get('profit_factor', 0):.2f}")
        logger.info(f"平均交易收益: {stats.get('avg_trade', 0):,.2f}")
        logger.info(f"最大单笔盈利: {stats.get('largest_win', 0):,.2f}")
        logger.info(f"最大单笔亏损: {stats.get('largest_loss', 0):,.2f}")
        logger.info(f"平均持仓天数: {stats.get('avg_bars_held', 0):.1f}")
        logger.info(f"总净利润: {stats.get('total_net_profit', 0):,.2f}")

@AnalyzerRegistry.register(
    name='position',
    order=40,
    enabled=True,
    description='分析持仓相关指标'
)
class PositionAnalyzer(BaseAnalyzer):
    """持仓分析器"""
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        cerebro.addanalyzer(bt.analyzers.PositionsValue, _name='positions')
        
    def _analyze(self, strategy) -> Dict[str, Any]:
        analysis = strategy.analyzers.positions.get_analysis()
        
        # 计算持仓统计
        positions = list(analysis.values())
        if positions:
            positions = np.array(positions)
            return {
                'position_metrics': {
                    'avg_position_size': float(np.mean(positions)),
                    'max_position_size': float(np.max(positions)),
                    'min_position_size': float(np.min(positions)),
                    'position_std': float(np.std(positions)),
                }
            }
        return {'position_metrics': {}} 
    
    def _print_results(self, results: Dict[str, Any]):
        """打印持仓分析结果"""
        metrics = results.get('position_metrics', {})
        if metrics:
            logger.info("\n====== 持仓分析 ======")
            logger.info(f"平均持仓规模: {metrics.get('avg_position_size', 0):,.2f}")
            logger.info(f"最大持仓规模: {metrics.get('max_position_size', 0):,.2f}")
            logger.info(f"最小持仓规模: {metrics.get('min_position_size', 0):,.2f}")
            logger.info(f"持仓波动性: {metrics.get('position_std', 0):,.2f}") 