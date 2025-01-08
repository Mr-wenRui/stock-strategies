import backtrader as bt
from typing import Dict, Any
from ..registry import AnalyzerRegistry

@AnalyzerRegistry.register('trade')
class TradeAnalyzer(bt.Analyzer):
    """交易分析器"""
    
    def __init__(self):
        super(TradeAnalyzer, self).__init__()
        self.trades = 0
        self.won = 0
        self.lost = 0
        self.total_won = 0.0
        self.total_lost = 0.0
        self.largest_won = 0.0
        self.largest_lost = 0.0
    
    def notify_trade(self, trade):
        if trade.status == trade.Closed:
            self.trades += 1
            
            if trade.pnl > 0:
                self.won += 1
                self.total_won += trade.pnl
                self.largest_won = max(self.largest_won, trade.pnl)
            else:
                self.lost += 1
                self.total_lost -= trade.pnl
                self.largest_lost = max(self.largest_lost, -trade.pnl)
    
    def get_analysis(self) -> Dict[str, Any]:
        return {
            'total_trades': self.trades,
            'won': self.won,
            'lost': self.lost,
            'win_rate': (self.won / self.trades * 100) if self.trades > 0 else 0,
            'profit_factor': (self.total_won / self.total_lost) if self.total_lost > 0 else 0,
            'average_won': self.total_won / self.won if self.won > 0 else 0,
            'average_lost': self.total_lost / self.lost if self.lost > 0 else 0,
            'largest_won': self.largest_won,
            'largest_lost': self.largest_lost
        } 