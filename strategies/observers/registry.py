import backtrader as bt
from typing import Dict, Type, Any
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class ObserverRegistry:
    """观察者注册表"""
    
    _observers: Dict[str, Dict[str, Any]] = {}  # 观察者字典
    
    @classmethod
    def register(cls, name: str):
        """注册观察者装饰器"""
        def decorator(observer_class):
            cls._observers[name] = {
                'class': observer_class,
                'enabled': True
            }
            logger.debug(f"注册观察者: {name}")
            return observer_class
        return decorator
    
    @classmethod
    def register_builtin(cls, name: str, observer_class: Type[bt.Observer]) -> None:
        """注册内置观察者"""
        cls._observers[name] = {
            'class': observer_class,
            'enabled': True
        }
        logger.debug(f"注册内置观察者: {name}")
    
    @classmethod
    def get_enabled_observers(cls) -> Dict[str, Type[bt.Observer]]:
        """获取已启用的观察者"""
        return {
            name: info['class'] 
            for name, info in cls._observers.items()
            if info.get('enabled', True)
        }
    
    @classmethod
    def is_enabled(cls, name: str) -> bool:
        """检查观察者是否启用"""
        if name in cls._observers:
            return cls._observers[name].get('enabled', True)
        return False
    
    @classmethod
    def enable(cls, name: str) -> None:
        """启用观察者"""
        if name in cls._observers:
            cls._observers[name]['enabled'] = True
            logger.debug(f"启用观察者: {name}")
    
    @classmethod
    def disable(cls, name: str) -> None:
        """禁用观察者"""
        if name in cls._observers:
            cls._observers[name]['enabled'] = False
            logger.debug(f"禁用观察者: {name}")
    
    @classmethod
    def reset(cls) -> None:
        """重置注册表"""
        cls._observers.clear()
        logger.debug("重置观察者注册表") 