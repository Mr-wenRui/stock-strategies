import backtrader as bt
import numpy as np
from typing import Dict, Any
from ..registry import AnalyzerRegistry

@AnalyzerRegistry.register('var')
class VaRAnalyzer(bt.Analyzer):
    """风险价值(VaR)分析器"""
    
    params = (
        ('confidence', 0.95),  # 置信水平
        ('period', 20),        # 计算周期
    )
    
    def __init__(self):
        super(VaRAnalyzer, self).__init__()
        self.returns = []
        self._value_start = None
    
    def next(self):
        value = self.strategy.broker.getvalue()
        if self._value_start is not None:
            ret = (value / self._value_start) - 1
            self.returns.append(ret)
        self._value_start = value
    
    def get_analysis(self) -> Dict[str, Any]:
        if len(self.returns) < self.p.period:
            return {'var': 0.0}
        
        # 使用最近period个数据计算VaR
        recent_returns = np.array(self.returns[-self.p.period:])
        var = np.percentile(recent_returns, (1 - self.p.confidence) * 100)
        
        return {'var': abs(var) * 100}  # 转换为百分比 