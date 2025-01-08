import backtrader as bt
import numpy as np
from typing import Dict, Any, List
from ..registry import AnalyzerRegistry

@AnalyzerRegistry.register('sortino')
class SortinoAnalyzer(bt.Analyzer):
    """索提诺比率分析器"""
    
    params = (
        ('risk_free_rate', 0.03),  # 年化无风险利率
        ('timeframe', bt.TimeFrame.Days),  # 时间框架
    )
    
    def __init__(self):
        super(SortinoAnalyzer, self).__init__()
        self.returns = []
        self._value_start = None
    
    def start(self):
        super(SortinoAnalyzer, self).start()
        self._value_start = self.strategy.broker.getvalue()
    
    def next(self):
        value = self.strategy.broker.getvalue()
        ret = (value / self._value_start) - 1
        self.returns.append(ret)
        self._value_start = value
    
    def get_analysis(self) -> Dict[str, Any]:
        if not self.returns:
            return {'sortino_ratio': 0.0}
        
        returns = np.array(self.returns)
        rfr = self.p.risk_free_rate / 252  # 日化无风险利率
        excess_returns = returns - rfr
        
        # 只考虑负收益的标准差
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) > 0:
            downside_std = np.std(downside_returns, ddof=1)
            if downside_std > 0:
                sortino = np.mean(excess_returns) / downside_std * np.sqrt(252)
            else:
                sortino = 0.0
        else:
            sortino = 0.0
        
        return {'sortino_ratio': sortino} 