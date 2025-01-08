from typing import Dict, Any
from utils.logger import Logger
from .base_handler import ResultHandler

logger = Logger.get_logger(__name__)

class ConsoleHandler(ResultHandler):
    """控制台输出处理器"""
    
    def _register_handlers(self) -> None:
        """注册事件处理器"""
        # 只订阅关心的事件
        self.subscribe('final_result', self.handle_final_result)
        self.subscribe('trade_stats', self.handle_trade_result)
    
    def handle_final_result(self, result: Dict[str, Any]) -> None:
        """处理最终结果"""
        logger.info("\n" + "="*50)
        logger.info("回测结果摘要")
        logger.info("="*50)
        
        logger.info(f"初始资金: {result.get('initial_cash', 0):,.2f}")
        logger.info(f"最终资金: {result.get('final_value', 0):,.2f}")
        logger.info(f"总收益率: {result.get('returns', 0):+.2f}%")
        
        # 处理分析器结果
        if analyzer_results := result.get('analyzer_results'):
            self._print_analyzer_results(analyzer_results)
    
    def handle_trade_result(self, result: Dict[str, Any]) -> None:
        """处理交易结果"""
        logger.info("交易统计:")
        logger.info(f"总交易次数: {result.get('total_trades', 0)}")
        logger.info(f"胜率: {result.get('win_rate', 0):.2f}%")
        logger.info(f"盈亏比: {result.get('profit_factor', 0):.2f}")
    
    def _print_analyzer_results(self, analyzer_results: Dict[str, Any]) -> None:
        """打印分析器结果"""
        for name, result in analyzer_results.items():
            if name in ['returns', 'sharpe', 'drawdown']:  # 只打印关心的分析器结果
                logger.info(f"{name.upper()} 分析结果:")
                for key, value in result.items():
                    logger.info(f"{key}: {value}") 