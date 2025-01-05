from typing import Dict, Type, Any
import backtrader as bt

class ObserverRegistry:
    """观察者注册器"""
    
    _observers: Dict[str, Type[bt.Observer]] = {}
    _enabled: Dict[str, bool] = {}
    
    @classmethod
    def register(cls, name: str) -> callable:
        """注册观察者的装饰器"""
        def decorator(observer_class: Type[bt.Observer]) -> Type[bt.Observer]:
            cls._observers[name] = observer_class
            cls._enabled[name] = True  # 默认启用
            return observer_class
        return decorator
    
    @classmethod
    def get_observer(cls, name: str) -> Type[bt.Observer]:
        """获取观察者类"""
        return cls._observers.get(name)
    
    @classmethod
    def enable(cls, name: str) -> None:
        """启用观察者"""
        if name in cls._observers:
            cls._enabled[name] = True
    
    @classmethod
    def disable(cls, name: str) -> None:
        """禁用观察者"""
        if name in cls._observers:
            cls._enabled[name] = False
    
    @classmethod
    def is_enabled(cls, name: str) -> bool:
        """检查观察者是否启用"""
        return cls._enabled.get(name, False)
    
    @classmethod
    def get_enabled_observers(cls) -> Dict[str, Type[bt.Observer]]:
        """获取所有启用的观察者"""
        return {name: obs for name, obs in cls._observers.items() 
                if cls._enabled.get(name, False)}
    
    @classmethod
    def reset(cls) -> None:
        """重置所有观察者状态"""
        cls._enabled = {name: True for name in cls._observers} 