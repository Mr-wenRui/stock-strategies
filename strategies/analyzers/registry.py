from typing import Dict, Type, List
from functools import wraps
from .base_analyzer import BaseAnalyzer

class AnalyzerRegistry:
    """
    分析器注册表
    用于管理和组织所有分析器，实现分析器的注册、启用/禁用等功能
    """
    
    # 存储所有已注册的分析器信息
    # 格式: {
    #   'analyzer_name': {
    #       'class': 分析器类,
    #       'enabled': 是否启用,
    #       'order': 执行顺序,
    #       'description': 分析器描述
    #   }
    # }
    _analyzers: Dict[str, Dict] = {}
    
    # 保存分析器的执行顺序，按order排序
    _order: List[str] = []
    
    @classmethod
    def register(cls, name: str, order: int = None, enabled: bool = True, description: str = None):
        """
        分析器注册装饰器
        用于注册新的分析器类，并设置其基本属性
        
        参数:
            name: 分析器唯一标识名
            order: 执行顺序（数字越小越先执行），默认为999
            enabled: 是否默认启用，默认为True
            description: 分析器描述，默认使用类文档字符串
        
        使用示例:
            @AnalyzerRegistry.register(
                name='my_analyzer',
                order=50,
                enabled=True,
                description='我的自定义分析器'
            )
            class MyAnalyzer(BaseAnalyzer):
                pass
        """
        def decorator(analyzer_class: Type[BaseAnalyzer]):
            # 保存分析器信息
            cls._analyzers[name] = {
                'class': analyzer_class,
                'enabled': enabled,
                'order': order or 999,
                'description': description or analyzer_class.__doc__,
                'instance': analyzer_class()  # 创建实例并保存
            }
            
            # 根据order值更新执行顺序列表
            if name not in cls._order:
                # 按order排序插入到正确位置
                for i, existing_name in enumerate(cls._order):
                    if order < cls._analyzers[existing_name]['order']:
                        cls._order.insert(i, name)
                        break
                else:
                    cls._order.append(name)
            
            return analyzer_class
        return decorator
    
    @classmethod
    def enable(cls, name: str):
        """
        启用指定的分析器
        
        参数:
            name: 分析器名称
        """
        if name in cls._analyzers:
            cls._analyzers[name]['enabled'] = True
        else:
            raise ValueError(f"未找到名为 '{name}' 的分析器")
    
    @classmethod
    def disable(cls, name: str):
        """
        禁用指定的分析器
        
        参数:
            name: 分析器名称
        """
        if name in cls._analyzers:
            cls._analyzers[name]['enabled'] = False
        else:
            raise ValueError(f"未找到名为 '{name}' 的分析器")
    
    @classmethod
    def get_analyzer_chain(cls) -> BaseAnalyzer:
        """
        创建并返回分析器责任链
        
        返回:
            责任链的头部分析器
            
        异常:
            ValueError: 当没有可用的分析器时抛出
        """
        # 获取所有已启用的分析器
        enabled_analyzers = [
            name for name in cls._order
            if name in cls._analyzers and cls._analyzers[name]['enabled']
        ]
        
        if not enabled_analyzers:
            raise ValueError("没有找到任何可用的分析器，请先注册一些分析器")
        
        # 使用已存在的实例创建责任链
        head = cls._analyzers[enabled_analyzers[0]]['instance']
        current = head
        
        # 按顺序连接所有启用的分析器
        for name in enabled_analyzers[1:]:
            analyzer = cls._analyzers[name]['instance']
            current.set_next(analyzer)
            current = analyzer
        
        return head 