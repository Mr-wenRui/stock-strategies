from typing import Dict, Any, List
import numpy as np
from utils.logger import Logger
from .base_observer import BaseObserver
from .registry import ObserverRegistry

logger = Logger.get_logger(__name__)

@ObserverRegistry.register('returns')
class ReturnsObserver(BaseObserver):
    """简单收益率观察者
    跟踪策略的收益率变化
    """
    lines = ('returns',)
    plotinfo = dict(plot=True, subplot=True, plotname='收益率 %')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial_value = self._owner.broker.startingcash

    def next(self):
        """计算并更新收益率"""
        try:
            # current_value = self._owner.broker.getvalue()
            # initial_value = self._owner.broker.startingcash
            current_value = self._owner.broker.getvalue()
            
            # 计算收益率（百分比）
            returns = ((current_value / self.initial_value) - 1) * 100
            self.lines.returns[0] = returns
            
        except Exception as e:
            logger.error(f"计算收益率失败: {str(e)}")
            self.lines.returns[0] = 0
    
    def get_analysis(self) -> Dict[str, Any]:
        """获取分析结果"""
        last_values = self.get_last_values()
        return {
            'current': {
                'returns': self.format_percentage(last_values.get('returns', 0))
            },
            'series': self.get_series()
        }
    
    def print_analysis(self) -> None:
        """打印分析结果"""
        last_values = self.get_last_values()
        logger.info("\n收益率分析:")
        logger.info(f"当前收益率: {self.format_percentage(last_values.get('returns', 0))}") 