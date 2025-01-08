from typing import Dict, Any
from utils.logger import Logger
from .base_observer import BaseObserver
from .registry import ObserverRegistry

logger = Logger.get_logger(__name__)

@ObserverRegistry.register('drawdown')
class DrawdownObserver(BaseObserver):
    """回撤观察者"""
    
    lines = ('drawdown',)
    plotinfo = dict(plot=True, subplot=True, plotname='回撤 %')
    
    def __init__(self):
        super().__init__()
        self.peak = float('-inf')
    
    def next(self):
        """计算并更新回撤"""
        try:
            value = self._owner.broker.getvalue()
            
            # 更新峰值
            if value > self.peak:
                self.peak = value
            
            # 计算回撤
            if self.peak > 0:
                drawdown = (self.peak - value) / self.peak * 100
            else:
                drawdown = 0
            
            self.lines.drawdown[0] = drawdown
            
        except Exception as e:
            logger.error(f"计算回撤失败: {str(e)}")
            self.lines.drawdown[0] = 0 