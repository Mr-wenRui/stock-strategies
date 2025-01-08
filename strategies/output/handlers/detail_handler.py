from typing import Dict, Any
from utils.logger import Logger
from .base_handler import ResultHandler

logger = Logger.get_logger(__name__)

class DetailHandler(ResultHandler):
    """详细信息处理器"""
    
    def _register_handlers(self) -> None:
        """注册事件处理器"""
        # 订阅所有事件
        self.subscribe('analyzer_result', self.handle_analyzer_result)
        self.subscribe('observer_result', self.handle_observer_result)
        self.subscribe('trade_stats', self.handle_trade_result)
        self.subscribe('basic_info', self.handle_basic_info)
        self.subscribe('error', self.handle_error)
    
    def handle_analyzer_result(self, data: Dict[str, Any]) -> None:
        """处理分析器结果"""
        name = data['name']
        result = data['result']
        logger.debug(f"分析器 {name} 结果:")
        for key, value in result.items():
            logger.debug(f"{key}: {value}")
    
    def handle_observer_result(self, data: Dict[str, Any]) -> None:
        """处理观察者结果"""
        name = data['name']
        result = data['result']
        if current := result.get('current'):
            logger.debug(f"观察者 {name} 当前值:")
            for key, value in current.items():
                logger.debug(f"{key}: {value}")
    
    def handle_trade_result(self, result: Dict[str, Any]) -> None:
        """处理交易结果"""
        logger.debug("详细交易统计:")
        for key, value in result.items():
            logger.debug(f"{key}: {value}")
    
    def handle_basic_info(self, info: Dict[str, Any]) -> None:
        """处理基本信息"""
        logger.debug("基本信息:")
        for key, value in info.items():
            logger.debug(f"{key}: {value}")
    
    def handle_error(self, error: str) -> None:
        """处理错误信息"""
        logger.error(f"\n发生错误: {error}") 