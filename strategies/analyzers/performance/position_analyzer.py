import backtrader as bt
from typing import Dict, Any
from collections import defaultdict
from ..registry import AnalyzerRegistry

@AnalyzerRegistry.register('position')
class PositionAnalyzer(bt.Analyzer):
    """持仓分析器"""
    
    def __init__(self):
        super(PositionAnalyzer, self).__init__()
        self.positions = defaultdict(int)
        self.position_value = defaultdict(float)
        self.max_positions = 0
        self.current_positions = 0
    
    def next(self):
        # 更新持仓信息
        total_value = self.strategy.broker.getvalue()
        self.current_positions = 0
        
        for data in self.strategy.datas:
            position = self.strategy.getposition(data)
            if position.size != 0:
                self.current_positions += 1
                self.positions[data._name] = position.size
                self.position_value[data._name] = position.size * data.close[0]
        
        self.max_positions = max(self.max_positions, self.current_positions)
    
    def get_analysis(self) -> Dict[str, Any]:
        return {
            'max_positions': self.max_positions,
            'current_positions': self.current_positions,
            'positions': dict(self.positions),
            'position_value': dict(self.position_value)
        } 