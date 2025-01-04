from abc import ABC, abstractmethod
from typing import Dict, Any
import backtrader as bt
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class BaseAnalyzer(ABC):
    """
    分析器基类
    
    调用链：
    1. 创建分析器实例
    2. 通过 set_next 构建责任链
    3. 通过 add_to_cerebro 添加到回测引擎
    4. 回测完成后通过 get_analysis_results 获取结果
    """
    
    def __init__(self):
        # 责任链中的下一个分析器
        self._next = None
    
    def set_next(self, analyzer: 'BaseAnalyzer') -> 'BaseAnalyzer':
        """
        设置责任链中的下一个分析器
        
        调用流程：
        1. create_default_chain 中调用本方法
        2. 设置下一个分析器
        3. 返回下一个分析器以支持链式调用
        """
        self._next = analyzer
        return analyzer
    
    def add_to_cerebro(self, cerebro: bt.Cerebro):
        """
        将分析器添加到cerebro中
        
        调用流程：
        1. add_analyzers 调用本方法
        2. 调用 _add_analyzer 添加当前分析器
        3. 递归调用下一个分析器的 add_to_cerebro
        """
        # 添加当前分析器
        self._add_analyzer(cerebro)
        # 递归添加后继分析器
        if self._next:
            self._next.add_to_cerebro(cerebro)
    
    def get_analysis_results(self, strategy) -> Dict[str, Any]:
        """
        获取分析结果并打印
        
        调用流程：
        1. get_analysis_results 调用本方法
        2. 调用 _analyze 获取当前分析器结果
        3. 调用 _print_results 打印当前分析器结果
        4. 递归调用下一个分析器的 get_analysis_results
        5. 合并所有结果并返回
        """
        # 获取当前分析器的结果
        results = self._analyze(strategy)
        
        # 打印当前分析器的结果
        self._print_results(results)
        
        # 递归获取后继分析器的结果并合并
        if self._next:
            results.update(self._next.get_analysis_results(strategy))
        
        return results
    
    @abstractmethod
    def _add_analyzer(self, cerebro: bt.Cerebro):
        """
        添加具体的分析器到cerebro（由子类实现）
        
        Args:
            cerebro: Backtrader的cerebro对象
        """
        pass
    
    @abstractmethod
    def _analyze(self, strategy) -> Dict[str, Any]:
        """
        执行具体的分析（由子类实现）
        
        Args:
            strategy: 策略对象，包含分析器实例
            
        Returns:
            分析结果字典
        """
        pass 
    
    def _print_results(self, results: Dict[str, Any]):
        """打印分析结果（可由子类重写）"""
        pass 