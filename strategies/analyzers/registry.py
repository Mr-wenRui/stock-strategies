from typing import Dict, Type, Any
import backtrader as bt
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class AnalyzerRegistry:
    """分析器注册表"""
    
    _analyzers: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str):
        """注册分析器装饰器"""
        def decorator(analyzer_class: Type[bt.Analyzer]):
            cls._analyzers[name] = {
                'class': analyzer_class,
                'enabled': True
            }
            logger.debug(f"注册分析器: {name}")
            return analyzer_class
        return decorator
    
    @classmethod
    def get_analyzer_class(cls, name: str) -> Type[bt.Analyzer]:
        """获取分析器类"""
        if name not in cls._analyzers:
            raise ValueError(f"未找到分析器: {name}")
        return cls._analyzers[name]['class']
    
    @classmethod
    def get_enabled_analyzers(cls) -> Dict[str, Dict[str, Any]]:
        """获取已启用的分析器"""
        return {
            name: info for name, info in cls._analyzers.items()
            if info.get('enabled', True)
        }
    
    @classmethod
    def enable(cls, name: str) -> None:
        """启用分析器"""
        if name in cls._analyzers:
            cls._analyzers[name]['enabled'] = True
            logger.debug(f"启用自定义分析器: {name}")
    
    @classmethod
    def disable(cls, name: str) -> None:
        """禁用分析器"""
        if name in cls._analyzers:
            cls._analyzers[name]['enabled'] = False
            logger.debug(f"禁用分析器: {name}")
    
    @classmethod
    def reset(cls) -> None:
        """重置注册表"""
        cls._analyzers.clear()
        logger.debug("重置分析器注册表") 