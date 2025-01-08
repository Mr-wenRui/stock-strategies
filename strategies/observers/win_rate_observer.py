from typing import Dict, Any
from utils.logger import Logger
from .base_observer import BaseObserver
from .registry import ObserverRegistry

logger = Logger.get_logger(__name__)

@ObserverRegistry.register('win_rate')
class WinRateObserver(BaseObserver):
    """胜率观察者"""
    
    lines = ('win_rate',)
    plotinfo = dict(plot=True, subplot=True, plotname='胜率 %')
    
    def __init__(self):
        super().__init__()
        self.total_trades = 0
        self.won_trades = 0
    
    def next(self):
        """更新胜率"""
        try:
            # 从交易分析器获取数据
            analyzer = next(
                (a for a in self._owner.analyzers 
                 if getattr(a, '_name', getattr(a, 'name', '')).lower() == 'trade'),
                None
            )
            
            if analyzer:
                analysis = analyzer.get_analysis()
                total = analysis.get('total', 0)
                won = analysis.get('won', 0)
                
                win_rate = (won / total * 100) if total > 0 else 0
                self.lines.win_rate[0] = win_rate
            else:
                self.lines.win_rate[0] = 0
                
        except Exception as e:
            logger.error(f"计算胜率失败: {str(e)}")
            self.lines.win_rate[0] = 0 