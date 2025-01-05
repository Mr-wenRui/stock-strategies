from typing import Dict, Any, List, Type
import backtrader as bt
import numpy as np
from utils.logger import Logger
from ..notifications.record_manager import RecordManager
from ..analyzers.analyzer_chain import AnalyzerChainBuilder
from ..observers.base_observer import BaseObserver

logger = Logger.get_logger(__name__)

class ResultCollector:
    """回测结果收集器"""
    
    @classmethod
    def collect_results(cls, strategy: bt.Strategy, cerebro: bt.Cerebro, 
                       init_cash: float) -> Dict[str, Any]:
        """收集回测结果"""
        try:
            # 1. 收集基础信息
            basic_info = cls._collect_basic_info(cerebro, init_cash)
            
            # 2. 收集分析器结果
            analyzer_results = cls._collect_analyzer_results(strategy)
            
            # 3. 收集观察者数据
            observer_data = cls._collect_observer_data(strategy)
            
            # 4. 收集交易统计
            trade_stats = cls._collect_trade_stats()
            
            # 合并所有结果
            final_results = {
                'success': True,
                **basic_info,
                **analyzer_results,
                'observer_data': observer_data,
                'trade_stats': trade_stats
            }
            
            return final_results
            
        except Exception as e:
            error_msg = f"收集回测结果失败: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @staticmethod
    def _collect_basic_info(cerebro: bt.Cerebro, init_cash: float) -> Dict[str, Any]:
        """收集基础信息"""
        portfolio_value = cerebro.broker.getvalue()
        returns = (portfolio_value / init_cash - 1) * 100
        
        return {
            'initial_cash': init_cash,
            'final_value': portfolio_value,
            'returns': returns,
            'profit': portfolio_value - init_cash
        }
    
    @staticmethod
    def _collect_analyzer_results(strategy: bt.Strategy) -> Dict[str, Any]:
        """收集分析器结果"""
        if hasattr(strategy, 'analyzers'):
            return AnalyzerChainBuilder.get_analysis_results(
                strategy, strategy.analyzers)
        return {}
    
    @classmethod
    def _collect_observer_data(cls, strategy: bt.Strategy) -> Dict[str, Any]:
        """收集观察者数据"""
        observer_data = {}
        
        # 遍历所有观察者
        for observer in strategy.observers:
            if isinstance(observer, BaseObserver):
                # 获取观察者名称
                observer_name = observer.__class__.__name__.lower()
                # 收集观察者数据
                observer_data[observer_name] = observer.get_analysis()
                # 打印观察者分析结果
                observer.print_analysis()
        
        return observer_data
    
    @staticmethod
    def _collect_trade_stats() -> Dict[str, Any]:
        """收集交易统计"""
        return RecordManager.get_instance().get_trade_summary() 