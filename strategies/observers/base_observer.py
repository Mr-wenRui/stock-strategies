import backtrader as bt
from typing import Dict, Any, List, Optional, Type
from abc import abstractmethod
import numpy as np
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class BaseObserver(bt.Observer):
    """观察者基类"""
    
    plotinfo = dict(plot=True)
    
    @classmethod
    def get_observer(cls, strategy: bt.Strategy) -> Optional['BaseObserver']:
        """获取观察者实例"""
        if not hasattr(strategy, 'observers'):
            return None
        
        return next(
            (obs for obs in strategy.observers if isinstance(obs, cls)),
            None
        )
    
    @classmethod
    def get_latest_value(cls, strategy: bt.Strategy, line_name: str) -> float:
        """获取最新值"""
        observer = cls.get_observer(strategy)
        if observer is None:
            return 0.0
        
        try:
            line = getattr(observer.lines, line_name)
            return line[0]
        except Exception:
            return 0.0
    
    @classmethod
    def get_series(cls, strategy: bt.Strategy, line_name: str) -> List[float]:
        """获取数据序列"""
        observer = cls.get_observer(strategy)
        if observer is None:
            return []
        
        try:
            line = getattr(observer.lines, line_name)
            return list(line.array)
        except Exception:
            return []
    
    def get_all_series(self) -> Dict[str, List[float]]:
        """获取所有数据序列"""
        series = {}
        for linename in self.lines._getlines():
            line = getattr(self.lines, linename)
            series[linename] = list(line.array)
        return series
    
    def get_last_values(self) -> Dict[str, float]:
        """获取最新值"""
        values = {}
        for linename in self.lines._getlines():
            line = getattr(self.lines, linename)
            values[linename] = line[0]
        return values
    
    def get_analysis(self) -> Dict[str, Any]:
        """获取分析结果"""
        return {
            'current': self.get_last_values(),
            'series': self.get_all_series()
        }
    
    @staticmethod
    def format_percentage(value: float) -> str:
        """格式化百分比"""
        return f"{value:+.2f}%"
    
    def next(self) -> None:
        """更新观察者数据"""
        raise NotImplementedError("子类必须实现 next() 方法")
    
    def _process_data(self, data: List[float]) -> List[float]:
        """处理数据序列，过滤无效值"""
        return [x for x in data if not np.isnan(x)]
    
    def format_value(self, value: float, format_str: str = '{:.2f}') -> str:
        """格式化数值"""
        try:
            return format_str.format(value)
        except (ValueError, TypeError):
            return str(value)
    
    def format_currency(self, value: float) -> str:
        """格式化货币"""
        return f"{value:,.2f}"
    
    @abstractmethod
    def print_analysis(self) -> None:
        """打印分析结果"""
        pass 