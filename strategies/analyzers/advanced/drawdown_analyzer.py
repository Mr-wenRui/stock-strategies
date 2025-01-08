import backtrader as bt
from typing import Dict, Any
from ..registry import AnalyzerRegistry

@AnalyzerRegistry.register('drawdown')
class DrawdownAnalyzer(bt.Analyzer):
    """回撤分析器"""
    
    params = (
        ('max_dd_limit', 20.0),  # 最大回撤限制
    )
    
    def __init__(self):
        super(DrawdownAnalyzer, self).__init__()
        self.max_dd = 0.0
        self.current_dd = 0.0
        self.peak = float('-inf')
    
    def next(self):
        value = self.strategy.broker.getvalue()
        
        # 更新峰值
        if value > self.peak:
            self.peak = value
        
        # 计算当前回撤
        if self.peak > 0:
            self.current_dd = (self.peak - value) / self.peak * 100
            self.max_dd = max(self.max_dd, self.current_dd)
    
    def get_analysis(self) -> Dict[str, Any]:
        return {
            'max_drawdown': self.max_dd,
            'current_drawdown': self.current_dd
        } 