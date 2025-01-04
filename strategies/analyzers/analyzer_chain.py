from typing import Dict, Any
import backtrader as bt
from .registry import AnalyzerRegistry
from .base_analyzer import BaseAnalyzer
from . import (
    # 基础分析器
    SharpeAnalyzer,
    DrawdownAnalyzer,
    TradeAnalyzer,
    # 高级分析器
    ReturnsAnalyzer,
    RiskAnalyzer,
    TradeStatsAnalyzer,
    PositionAnalyzer
)

class AnalyzerChainBuilder:
    """
    分析器链构建器
    负责创建和管理分析器责任链，提供分析器链的构建和使用接口
    """
    
    @staticmethod
    def create_default_chain() -> BaseAnalyzer:
        """
        创建默认的分析器链
        直接使用已注册的分析器创建责任链
        
        返回:
            分析器责任链的头部分析器
        """
        return AnalyzerRegistry.get_analyzer_chain()
    
    @staticmethod
    def add_analyzers(cerebro: bt.Cerebro):
        """
        将分析器添加到回测引擎
        
        参数:
            cerebro: Backtrader的cerebro对象
            
        返回:
            分析器链对象，用于后续获取分析结果
        """
        analyzer_chain = AnalyzerChainBuilder.create_default_chain()
        analyzer_chain.add_to_cerebro(cerebro)
        return analyzer_chain
    
    @staticmethod
    def get_analysis_results(strategy, analyzer_chain: BaseAnalyzer) -> Dict[str, Any]:
        """
        获取所有分析器的分析结果
        
        参数:
            strategy: 策略对象
            analyzer_chain: 分析器链对象
            
        返回:
            包含所有分析结果的字典
        """
        return analyzer_chain.get_analysis_results(strategy) 