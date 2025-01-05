from typing import Dict, Any
import numpy as np
import backtrader as bt
from strategies.analyzers.base_analyzer import BaseAnalyzer
from strategies.analyzers.registry import AnalyzerRegistry
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
        try:
            time_analysis = strategy.analyzers.time_return.get_analysis()
            annual_analysis = strategy.analyzers.annual_return.get_analysis()
            
            # 计算月度收益率
            returns = list(time_analysis.values()) if time_analysis else []
            monthly_returns = np.array([])
            
            if returns:
                try:
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
                except Exception as e:
                    logger.error(f"计算月度收益率失败: {str(e)}")
            
            # 计算年化收益率（安全处理）
            annual_returns = list(annual_analysis.values()) if annual_analysis else []
            annual_return = float(np.mean(annual_returns)) if annual_returns else 0
            
            # 安全计算月度统计
            if len(monthly_returns) > 0:
                best_month = float(np.max(monthly_returns) * 100)
                worst_month = float(np.min(monthly_returns) * 100)
                avg_monthly = float(np.mean(monthly_returns) * 100)
            else:
                best_month = worst_month = avg_monthly = 0
            
            return {
                'returns_metrics': {
                    'annual_return': float(annual_return * 100),  # 转换为百分比
                    'monthly_returns': monthly_returns.tolist() if len(monthly_returns) > 0 else [],
                    'best_month': best_month,
                    'worst_month': worst_month,
                    'avg_monthly_return': avg_monthly
                }
            }
        except Exception as e:
            logger.error(f"收益率分析失败: {str(e)}")
            return {
                'returns_metrics': {
                    'annual_return': 0,
                    'monthly_returns': [],
                    'best_month': 0,
                    'worst_month': 0,
                    'avg_monthly_return': 0
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
        try:
            # 安全获取收益率数据
            returns_analysis = strategy.analyzers.returns.get_analysis()
            returns = list(returns_analysis.values()) if returns_analysis else []
            drawdown = strategy.analyzers.drawdown.get_analysis()
            
            # 计算风险指标（添加安全检查）
            if returns:
                returns_array = np.array(returns)
                # 年化波动率
                volatility = float(np.std(returns_array) * np.sqrt(252)) if len(returns_array) > 0 else 0
                
                # 下行波动率
                downside_returns = returns_array[returns_array < 0]
                downside_vol = float(np.std(downside_returns) * np.sqrt(252)) if len(downside_returns) > 0 else 0
            else:
                volatility = downside_vol = 0
            
            # 安全获取回撤数据
            max_dd = drawdown.get('max', {})
            avg_dd = drawdown.get('average', {})
            
            return {
                'risk_metrics': {
                    'volatility': volatility * 100,  # 转换为百分比
                    'downside_volatility': downside_vol * 100,
                    'max_drawdown': float(max_dd.get('drawdown', 0) or 0) * 100,
                    'max_drawdown_duration': int(max_dd.get('len', 0) or 0),
                    'avg_drawdown': float(avg_dd.get('drawdown', 0) or 0) * 100,
                    'avg_drawdown_duration': int(avg_dd.get('len', 0) or 0),
                }
            }
        except Exception as e:
            logger.error(f"风险分析失败: {str(e)}")
            return {
                'risk_metrics': {
                    'volatility': 0,
                    'downside_volatility': 0,
                    'max_drawdown': 0,
                    'max_drawdown_duration': 0,
                    'avg_drawdown': 0,
                    'avg_drawdown_duration': 0,
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
        
        # 安全计算盈亏比
        gross_won = gross.get('won', 0)
        gross_lost = abs(gross.get('lost', 0))  # 确保是正数
        profit_factor = gross_won / gross_lost if gross_lost != 0 else 0
        
        return {
            'trade_statistics': {
                'total_trades': total,
                'won_trades': won,
                'lost_trades': lost,
                'win_rate': (won / total * 100) if total > 0 else 0,
                'profit_factor': profit_factor,
                'avg_trade': net.get('average', 0) or 0,  # 使用 or 0 避免 None
                'avg_win': analysis.get('won', {}).get('pnl', {}).get('average', 0) or 0,
                'avg_loss': analysis.get('lost', {}).get('pnl', {}).get('average', 0) or 0,
                'largest_win': analysis.get('won', {}).get('pnl', {}).get('max', 0) or 0,
                'largest_loss': analysis.get('lost', {}).get('pnl', {}).get('max', 0) or 0,
                'avg_bars_held': avg_bars or 0,
                'total_net_profit': net.get('total', 0) or 0,
                'total_gross_profit': gross.get('total', 0) or 0,
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
        """添加分析器到回测引擎"""
        class _PositionAnalyzer(bt.Analyzer):
            params = (
                ('log', False),  # 是否打印日志
            )
            
            def __init__(self):
                super(_PositionAnalyzer, self).__init__()
                self.position_history = []  # 持仓历史
                self.position_sizes = []    # 持仓规模历史
                self.position_values = []   # 持仓市值历史
                self.position_durations = []  # 持仓周期历史
                self.current_positions = {}   # 当前持仓
            
            def notify_trade(self, trade):
                """处理交易通知"""
                try:
                    if trade.status == trade.Closed and trade.history:  # 确保有交易历史
                        # 记录持仓周期
                        duration = len(trade.history)
                        if duration > 0:  # 确保有效的持仓周期
                            self.position_durations.append(duration)
                            
                            # 安全计算平均持仓规模
                            total_size = sum(abs(t.size) for t in trade.history)
                            avg_size = total_size / duration
                            self.position_sizes.append(avg_size)
                            
                            # 安全计算平均持仓市值
                            total_value = sum(abs(t.value) for t in trade.history)
                            avg_value = total_value / duration
                            self.position_values.append(avg_value)
                except Exception as e:
                    self.strategy.logger.error(f"处理交易通知失败: {str(e)}")
            
            def next(self):
                """更新持仓信息"""
                try:
                    total_value = 0
                    total_size = 0
                    
                    for data in self.strategy.datas:
                        position = self.strategy.getposition(data)
                        if position.size != 0:
                            if data not in self.current_positions:
                                self.current_positions[data] = {
                                    'size': position.size,
                                    'value': position.size * data.close[0],
                                    'entry_date': len(self.strategy)
                                }
                            
                            total_size += abs(position.size)
                            total_value += abs(position.size * data.close[0])
                    
                    self.position_history.append({
                        'total_size': total_size,
                        'total_value': total_value,
                        'positions': len([p for p in self.strategy.positions.values() if p.size != 0])
                    })
                except Exception as e:
                    self.strategy.logger.error(f"更新持仓信息失败: {str(e)}")
            
            def get_analysis(self):
                """获取分析结果"""
                try:
                    # 安全计算平均值
                    avg_duration = float(np.mean(self.position_durations)) if self.position_durations else 0
                    avg_size = float(np.mean(self.position_sizes)) if self.position_sizes else 0
                    avg_value = float(np.mean(self.position_values)) if self.position_values else 0
                    
                    # 安全计算持仓集中度
                    max_positions = max((h['positions'] for h in self.position_history), default=0)
                    avg_positions = float(np.mean([h['positions'] for h in self.position_history])) if self.position_history else 0
                    
                    # 安全计算换手率
                    turnover_rate = 0
                    if len(self.position_history) > 1:
                        position_changes = sum(
                            abs(self.position_history[i]['total_size'] - self.position_history[i-1]['total_size'])
                            for i in range(1, len(self.position_history))
                        )
                        avg_position_value = float(np.mean([h['total_value'] for h in self.position_history]))
                        if avg_position_value > 0:
                            turnover_rate = position_changes / (2 * avg_position_value)
                    
                    return {
                        'position': {
                            'avg_duration': avg_duration,
                            'avg_size': avg_size,
                            'avg_value': avg_value,
                            'max_positions': max_positions,
                            'avg_positions': avg_positions,
                            'turnover_rate': turnover_rate,
                            'history': self.position_history
                        }
                    }
                except Exception as e:
                    self.strategy.logger.error(f"获取分析结果失败: {str(e)}")
                    return {
                        'position': {
                            'avg_duration': 0,
                            'avg_size': 0,
                            'avg_value': 0,
                            'max_positions': 0,
                            'avg_positions': 0,
                            'turnover_rate': 0,
                            'history': []
                        }
                    }
        
        cerebro.addanalyzer(_PositionAnalyzer, _name='position_analyzer')
    
    def _analyze(self, strategy) -> Dict[str, Any]:
        """分析持仓数据"""
        return strategy.analyzers.position_analyzer.get_analysis()
    
    def _print_results(self, results: Dict[str, Any]):
        """打印持仓分析结果"""
        position_data = results.get('position', {})
        logger.info("\n====== 持仓分析 ======")
        logger.info(f"平均持仓周期: {position_data.get('avg_duration', 0):.1f}天")
        logger.info(f"平均持仓规模: {position_data.get('avg_size', 0):,.0f}股")
        logger.info(f"平均持仓市值: {position_data.get('avg_value', 0):,.2f}")
        logger.info(f"最大同时持仓: {position_data.get('max_positions', 0)}个")
        logger.info(f"平均持仓数量: {position_data.get('avg_positions', 0):.1f}个")
        logger.info(f"换手率: {position_data.get('turnover_rate', 0):.2%}") 

@AnalyzerRegistry.register(
    name='sharpe',
    order=10,
    enabled=True,
    description='计算夏普比率'
)
class SharpeAnalyzer(BaseAnalyzer):
    """夏普比率分析器"""
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        """添加分析器到回测引擎"""
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, 
                           _name='sharpe',
                           riskfreerate=0.02,  # 无风险利率
                           annualize=True,     # 年化
                           timeframe=bt.TimeFrame.Days)
    
    def _analyze(self, strategy) -> Dict[str, Any]:
        """分析夏普比率"""
        sharpe = strategy.analyzers.sharpe.get_analysis()
        return {
            'sharpe_ratio': float(sharpe.get('sharperatio', 0))
        }
    
    def _print_results(self, results: Dict[str, Any]):
        """打印夏普比率分析结果"""
        sharpe = results.get('sharpe_ratio', 0)
        logger.info("\n====== 夏普比率分析 ======")
        logger.info(f"夏普比率: {sharpe:.2f}")

@AnalyzerRegistry.register(
    name='drawdown',
    order=20,
    enabled=True,
    description='计算回撤相关指标'
)
class DrawdownAnalyzer(BaseAnalyzer):
    """回撤分析器"""
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        """添加分析器到回测引擎"""
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    
    def _analyze(self, strategy) -> Dict[str, Any]:
        """分析回撤数据"""
        drawdown = strategy.analyzers.drawdown.get_analysis()
        return {
            'drawdown': {
                'max': {
                    'drawdown': drawdown.get('max', {}).get('drawdown', 0) * 100,
                    'moneydown': drawdown.get('max', {}).get('moneydown', 0),
                    'length': drawdown.get('max', {}).get('len', 0),
                },
                'average': {
                    'drawdown': drawdown.get('average', {}).get('drawdown', 0) * 100,
                    'moneydown': drawdown.get('average', {}).get('moneydown', 0),
                    'length': drawdown.get('average', {}).get('len', 0),
                }
            }
        }
    
    def _print_results(self, results: Dict[str, Any]):
        """打印回撤分析结果"""
        dd = results.get('drawdown', {})
        max_dd = dd.get('max', {})
        avg_dd = dd.get('average', {})
        
        logger.info("\n====== 回撤分析 ======")
        logger.info(f"最大回撤: {max_dd.get('drawdown', 0):.2f}%")
        logger.info(f"最大回撤金额: {max_dd.get('moneydown', 0):,.2f}")
        logger.info(f"最长回撤期: {max_dd.get('length', 0)}天")
        logger.info(f"平均回撤: {avg_dd.get('drawdown', 0):.2f}%")
        logger.info(f"平均回撤金额: {avg_dd.get('moneydown', 0):,.2f}")
        logger.info(f"平均回撤期: {avg_dd.get('length', 0)}天")

@AnalyzerRegistry.register(
    name='trade',
    order=30,
    enabled=True,
    description='计算基础交易指标'
)
class TradeAnalyzer(BaseAnalyzer):
    """交易分析器"""
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        """添加分析器到回测引擎"""
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade')
    
    def _analyze(self, strategy) -> Dict[str, Any]:
        """分析交易数据"""
        trade = strategy.analyzers.trade.get_analysis()
        
        # 提取交易统计
        total = trade.get('total', {}).get('total', 0)
        won = trade.get('won', {}).get('total', 0)
        lost = trade.get('lost', {}).get('total', 0)
        
        return {
            'trade': {
                'total': total,
                'won': won,
                'lost': lost,
                'win_rate': (won / total * 100) if total > 0 else 0,
                'pnl': {
                    'gross': {
                        'total': trade.get('pnl', {}).get('gross', {}).get('total', 0),
                        'average': trade.get('pnl', {}).get('gross', {}).get('average', 0),
                    },
                    'net': {
                        'total': trade.get('pnl', {}).get('net', {}).get('total', 0),
                        'average': trade.get('pnl', {}).get('net', {}).get('average', 0),
                    }
                }
            }
        }
    
    def _print_results(self, results: Dict[str, Any]):
        """打印交易分析结果"""
        trade = results.get('trade', {})
        pnl = trade.get('pnl', {})
        
        logger.info("\n====== 交易分析 ======")
        logger.info(f"总交易次数: {trade.get('total', 0)}")
        logger.info(f"盈利交易: {trade.get('won', 0)}")
        logger.info(f"亏损交易: {trade.get('lost', 0)}")
        logger.info(f"胜率: {trade.get('win_rate', 0):.2f}%")
        logger.info(f"总盈亏: {pnl.get('net', {}).get('total', 0):,.2f}")
        logger.info(f"平均盈亏: {pnl.get('net', {}).get('average', 0):,.2f}") 