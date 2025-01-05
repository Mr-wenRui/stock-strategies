from typing import Dict, Any
import backtrader as bt
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class BaseAnalyzer:
    """分析器基类"""
    
    def add_to_cerebro(self, cerebro: bt.Cerebro):
        """添加分析器到回测引擎"""
        try:
            self._add_analyzer(cerebro)
        except Exception as e:
            logger.error(f"添加分析器失败: {str(e)}")
            raise
    
    def analyze(self, strategy) -> Dict[str, Any]:
        """执行分析"""
        try:
            results = self._analyze(strategy)
            self._print_results(results)
            return results
        except Exception as e:
            logger.error(f"分析失败: {str(e)}")
            return {}
    
    def _add_analyzer(self, cerebro: bt.Cerebro):
        """
        添加分析器到回测引擎
        子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 _add_analyzer 方法")
    
    def _analyze(self, strategy) -> Dict[str, Any]:
        """
        执行分析并返回结果
        子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 _analyze 方法")
    
    def _print_results(self, results: Dict[str, Any]):
        """
        打印分析结果
        子类必须实现此方法
        """
        raise NotImplementedError("子类必须实现 _print_results 方法") 