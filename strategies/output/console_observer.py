from typing import Dict, Any
from utils.logger import Logger
from .base_observer import OutputObserver

logger = Logger.get_logger(__name__)

class ConsoleObserver(OutputObserver):
    """控制台输出观察者"""
    
    def _process_basic_info(self, results: Dict[str, Any]) -> None:
        """处理基本信息"""
        logger.info("\n" + "="*50)
        logger.info("回测结果摘要")
        logger.info("="*50)
        
        # 基础信息
        logger.info(f"\n初始资金: {results.get('initial_cash', 0):,.2f}")
        logger.info(f"期末总值: {results.get('final_value', 0):,.2f}")
        logger.info(f"总收益率: {results.get('returns', 0):+.2f}%")
    
    def _process_trade_stats(self, stats: Dict[str, Any]) -> None:
        """处理交易统计"""
        if not stats:
            return
            
        logger.info("\n交易统计:")
        logger.info(f"总交易次数: {stats.get('total_trades', 0)}")
        logger.info(f"胜率: {stats.get('win_rate', 0):.2f}%")
        logger.info(f"盈亏比: {stats.get('profit_factor', 0):.2f}")
    
    def _process_observer_data(self, observer_data: Dict[str, Any]) -> None:
        """处理观察者数据"""
        if not observer_data:
            return
            
        # 只处理 returns observer 的数据
        returns_data = observer_data.get('returnsobserver', {})
        if returns_data:
            current = returns_data.get('current', {})
            logger.info(f"\n当前收益率: {current.get('returns', '0%')}")
    
    def _process_error(self, error: str) -> None:
        """处理错误信息"""
        logger.error(f"\n回测执行失败: {error}")
    
    def on_output(self, results: Dict[str, Any]) -> None:
        """处理输出结果"""
        try:
            if not results.get('success', True):
                self._process_error(results.get('error', '未知错误'))
                return
            
            # 基本信息
            self._process_basic_info(results)
            
            # 交易统计
            if 'trade_stats' in results:
                self._process_trade_stats(results['trade_stats'])
            
            # 观察者数据
            if 'observer_data' in results:
                self._process_observer_data(results['observer_data'])
            
            logger.info("\n" + "="*50 + "\n")
            
        except Exception as e:
            logger.error(f"输出结果失败: {str(e)}") 