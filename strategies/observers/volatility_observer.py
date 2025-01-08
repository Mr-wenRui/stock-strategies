from typing import Dict, Any
import numpy as np
from utils.logger import Logger
from .base_observer import BaseObserver
from .registry import ObserverRegistry

logger = Logger.get_logger(__name__)

@ObserverRegistry.register('volatility')
class VolatilityObserver(BaseObserver):
    """波动率观察者"""
    
    lines = ('volatility',)
    plotinfo = dict(plot=True, subplot=True, plotname='波动率 %')
    params = (
        ('period', 20),  # 计算周期
    )
    
    def __init__(self):
        super().__init__()
        self.returns = []
    
    def next(self):
        """计算并更新波动率"""
        try:
            current_value = self._owner.broker.getvalue()
            if len(self.returns) > 0:
                ret = (current_value / self.returns[-1]) - 1
                self.returns.append(current_value)
            else:
                ret = 0
                self.returns.append(current_value)
            
            # 计算波动率
            if len(self.returns) >= self.p.period:
                returns = np.array(self.returns[-self.p.period:])
                returns = np.diff(np.log(returns))
                volatility = np.std(returns, ddof=1) * np.sqrt(252) * 100
            else:
                volatility = 0
            
            self.lines.volatility[0] = volatility
            
        except Exception as e:
            logger.error(f"计算波动率失败: {str(e)}")
            self.lines.volatility[0] = 0 