from typing import Dict, Any, List, Optional
import backtrader as bt
from utils.logger import Logger
from utils.event_bus import EventBus
from ..analyzers.analyzer_chain import AnalyzerChainBuilder
from ..observers.base_observer import BaseObserver

logger = Logger.get_logger(__name__)

class ResultCollector:
    """回测结果收集器"""
    
    @classmethod
    def collect_results(cls, strategy: bt.Strategy, cerebro: bt.Cerebro, 
                       init_cash: float) -> Dict[str, Any]:
        """收集回测结果"""
        event_bus = EventBus.get_instance()
        try:
            # 1. 收集基础信息
            basic_info = cls._collect_basic_info(cerebro, init_cash)
            event_bus.publish('basic_info', basic_info)
            
            # 2. 收集分析器结果
            analyzer_results = cls._collect_analyzer_results(strategy)
            for name, result in analyzer_results.items():
                event_bus.publish('analyzer_result', {'name': name, 'result': result})
            
            # 3. 收集观察者数据
            observer_data = cls._collect_observer_data(strategy)
            for name, result in observer_data.items():
                event_bus.publish('observer_result', {'name': name, 'result': result})
            
            # 4. 收集交易统计
            trade_stats = cls._collect_trade_stats(strategy)
            event_bus.publish('trade_stats', trade_stats)
            
            # 合并所有结果
            final_results = {
                'success': True,
                **basic_info,
                'analyzer_results': analyzer_results,
                'observer_data': observer_data,
                'trade_stats': trade_stats
            }
            
            # 发布最终结果
            logger.debug(f"发布最终结果: {final_results}")
            event_bus.publish('final_result', final_results)
            
            return final_results
            
        except Exception as e:
            error_msg = f"收集回测结果失败: {str(e)}"
            logger.error(error_msg)
            event_bus.publish('error', error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    @staticmethod
    def _collect_basic_info(cerebro: bt.Cerebro, init_cash: float) -> Dict[str, float]:
        """收集基础信息"""
        try:
            portfolio_value = cerebro.broker.getvalue()
            returns = (portfolio_value / init_cash - 1) * 100
            
            return {
                'initial_cash': init_cash,
                'final_value': portfolio_value,
                'returns': returns,
                'profit': portfolio_value - init_cash
            }
        except Exception as e:
            logger.error(f"收集基础信息失败: {str(e)}")
            return {
                'initial_cash': init_cash,
                'final_value': 0.0,
                'returns': -100.0,
                'profit': -init_cash
            }
    
    @staticmethod
    def _collect_analyzer_results(strategy: bt.Strategy) -> Dict[str, Any]:
        """收集分析器结果"""
        try:
            if hasattr(strategy, 'analyzers'):
                return AnalyzerChainBuilder.get_analysis_results(
                    strategy, strategy.analyzers)
            return {}
        except Exception as e:
            logger.error(f"收集分析器结果失败: {str(e)}")
            return {}
    
    @classmethod
    def _collect_observer_data(cls, strategy: bt.Strategy) -> Dict[str, Any]:
        """收集观察者数据"""
        observer_data = {}
        try:
            # 遍历所有观察者
            for observer in strategy.observers:
                if isinstance(observer, BaseObserver):
                    try:
                        # 获取观察者名称
                        observer_name = observer.__class__.__name__.lower()
                        # 收集观察者数据
                        observer_data[observer_name] = observer.get_analysis()
                    except Exception as e:
                        logger.error(f"收集观察者 {observer.__class__.__name__} 数据失败: {str(e)}")
        except Exception as e:
            logger.error(f"收集观察者数据失败: {str(e)}")
        return observer_data
    
    @staticmethod
    def _collect_trade_stats(strategy: bt.Strategy) -> Dict[str, Any]:
        """收集交易统计"""
        try:
            # 从分析器结果中获取交易统计
            if hasattr(strategy, 'analyzers'):
                # 使用 getbyname 方法获取分析器
                trade_analyzer = strategy.analyzers.getbyname('trade')
                
                if trade_analyzer:
                    analysis = trade_analyzer.get_analysis()
                    logger.debug(f"交易分析器结果: {analysis}")
                    return analysis
                else:
                    logger.debug("未找到交易分析器")
            else:
                logger.debug("策略没有分析器属性")
            return {}
        except Exception as e:
            logger.error(f"收集交易统计失败: {str(e)}")
            return {} 