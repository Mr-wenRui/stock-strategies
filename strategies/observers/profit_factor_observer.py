from typing import Dict, Any
from utils.logger import Logger
from .base_observer import BaseObserver
from .registry import ObserverRegistry

logger = Logger.get_logger(__name__)

@ObserverRegistry.register('profit_factor')
class ProfitFactorObserver(BaseObserver):
    """盈亏比观察者"""
    
    lines = ('profit_factor',)
    plotinfo = dict(plot=True, subplot=True, plotname='盈亏比')
    
    def next(self):
        """更新盈亏比"""
        try:
            # 从交易分析器获取数据
            analyzer = next(
                (a for a in self._owner.analyzers 
                 if getattr(a, '_name', getattr(a, 'name', '')).lower() == 'trade'),
                None
            )
            
            if analyzer:
                analysis = analyzer.get_analysis()
                won = analysis.get('won', 0)
                lost = analysis.get('lost', 0)
                total_won = analysis.get('pnl/gross/won', 0)
                total_lost = abs(analysis.get('pnl/gross/lost', 0))
                
                profit_factor = (total_won / total_lost) if total_lost > 0 else 0
                self.lines.profit_factor[0] = profit_factor
            else:
                self.lines.profit_factor[0] = 0
                
        except Exception as e:
            logger.error(f"计算盈亏比失败: {str(e)}")
            self.lines.profit_factor[0] = 0 