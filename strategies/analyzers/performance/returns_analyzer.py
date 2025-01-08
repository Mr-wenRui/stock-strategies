import backtrader as bt
import numpy as np
from typing import Dict, Any
from ..registry import AnalyzerRegistry

@AnalyzerRegistry.register('returns')
class ReturnsAnalyzer(bt.Analyzer):
    """收益率分析器"""
    
    def __init__(self):
        super(ReturnsAnalyzer, self).__init__()
        self.returns = []
        self._value_start = None
    
    def start(self):
        super(ReturnsAnalyzer, self).start()
        self._value_start = self.strategy.broker.getvalue()
    
    def next(self):
        value = self.strategy.broker.getvalue()
        ret = (value / self._value_start) - 1
        self.returns.append(ret)
        self._value_start = value
    
    def get_analysis(self) -> Dict[str, Any]:
        if not self.returns:
            return {
                'total_return': 0.0,
                'annual_return': 0.0,
                'monthly_return': 0.0
            }
        
        total_return = self.returns[-1] * 100
        days = len(self.returns)
        
        # 年化收益率
        annual_return = ((1 + total_return/100) ** (252/days) - 1) * 100
        
        # 月均收益率
        monthly_return = ((1 + total_return/100) ** (21/days) - 1) * 100
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'monthly_return': monthly_return
        } 