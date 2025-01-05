from typing import Dict, Type, List, Any
import backtrader as bt
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class AnalyzerRegistry:
    """分析器注册表"""
    
    # 已注册的分析器
    _analyzers: Dict[str, Dict[str, Any]] = {}
    
    # 已启用的分析器
    _enabled_analyzers: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def register(cls, name: str, order: int = 100, enabled: bool = True, 
                description: str = ''):
        """
        注册分析器装饰器
        """
        def decorator(analyzer_class):
            # 创建分析器实例
            analyzer_instance = analyzer_class()
            cls._analyzers[name] = {
                'instance': analyzer_instance,
                'order': order,
                'enabled': enabled,
                'description': description
            }
            if enabled:
                cls._enabled_analyzers[name] = cls._analyzers[name]
            return analyzer_class
        return decorator
    
    @classmethod
    def enable(cls, name: str):
        """启用分析器"""
        if name in cls._analyzers:
            cls._enabled_analyzers[name] = cls._analyzers[name]
        else:
            logger.warning(f"未找到分析器: {name}")
    
    @classmethod
    def disable(cls, name: str):
        """禁用分析器"""
        cls._enabled_analyzers.pop(name, None)
    
    @classmethod
    def get_enabled_analyzers(cls) -> Dict[str, Dict[str, Any]]:
        """获取已启用的分析器"""
        return dict(sorted(
            cls._enabled_analyzers.items(),
            key=lambda x: x[1]['order']
        ))
    
    @classmethod
    def reset(cls):
        """重置分析器状态"""
        cls._enabled_analyzers = {
            name: info for name, info in cls._analyzers.items()
            if info['enabled']
        } 
    
    @classmethod
    def setup_analyzers(cls, analyzers: Dict[str, bool] = None) -> Dict[str, bool]:
        """配置分析器"""
        if analyzers is None:
            analyzers = {
                name: True for name in cls._analyzers.keys()
            }
        
        # 重置分析器状态
        cls.reset()
        
        # 更新分析器状态
        for name, enabled in analyzers.items():
            if enabled:
                cls.enable(name)
            else:
                cls.disable(name)
        
        return analyzers 