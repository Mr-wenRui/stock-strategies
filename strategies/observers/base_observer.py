import backtrader as bt
from typing import Dict, Any, List
from abc import abstractmethod
import numpy as np
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class BaseObserver(bt.Observer):
    """基础观察者类"""
    
    def get_analysis(self) -> Dict[str, Any]:
        """获取分析结果的默认实现"""
        return {name: list(line) for name, line in self.lines._getlines()}
    
    @abstractmethod
    def next(self) -> None:
        """更新观察者数据"""
        pass
    
    def get_last_values(self) -> Dict[str, float]:
        """获取最新值"""
        try:
            return {name: line[-1] for name, line in self.lines._getlines()}
        except Exception:
            return {}
    
    def get_series(self) -> Dict[str, List[float]]:
        """获取完整数据序列"""
        try:
            return {name: [x for x in line if not np.isnan(x)] 
                   for name, line in self.lines._getlines()}
        except Exception:
            return {}
    
    def _process_data(self, data: List[float]) -> List[float]:
        """处理数据序列，过滤无效值"""
        return [x for x in data if not np.isnan(x)]
    
    def format_value(self, value: float, format_str: str = '{:.2f}') -> str:
        """格式化数值"""
        try:
            return format_str.format(value)
        except (ValueError, TypeError):
            return str(value)
    
    def format_percentage(self, value: float) -> str:
        """格式化百分比"""
        return self.format_value(value) + '%'
    
    def format_currency(self, value: float) -> str:
        """格式化货币"""
        return f"{value:,.2f}"
    
    @abstractmethod
    def print_analysis(self) -> None:
        """打印分析结果"""
        pass 