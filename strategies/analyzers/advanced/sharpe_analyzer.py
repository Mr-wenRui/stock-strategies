import backtrader as bt
import numpy as np
from typing import Dict, Any, List
from ..registry import AnalyzerRegistry

@AnalyzerRegistry.register('sharpe')
class SharpeAnalyzer(bt.Analyzer):
    """夏普比率分析器"""
    
    params = (
        ('risk_free_rate', 0.03),  # 年化无风险利率
        ('timeframe', bt.TimeFrame.Days),  # 时间框架
    )
    
    def __init__(self):
        super(SharpeAnalyzer, self).__init__()
        self.returns = []
        self._value_start = None
    
    def start(self):
        super(SharpeAnalyzer, self).start()
        self._value_start = self.strategy.broker.getvalue()
    
    def next(self):
        # 计算收益率
        value = self.strategy.broker.getvalue()
        ret = (value / self._value_start) - 1
        self.returns.append(ret)
        self._value_start = value
    
    def get_analysis(self) -> Dict[str, Any]:
        if not self.returns:
            return {'sharpe_ratio': 0.0}
        
        # 计算年化夏普比率
        returns = np.array(self.returns)
        std = np.std(returns, ddof=1)
        
        if std > 0:
            rfr = self.p.risk_free_rate / 252  # 日化无风险利率
            excess_returns = returns - rfr
            sharpe = np.mean(excess_returns) / std * np.sqrt(252)
        else:
            sharpe = 0.0
        
        return {'sharpe_ratio': sharpe} 