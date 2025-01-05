from typing import Dict, Any, Set
from .base_observer import OutputObserver
from .console_observer import ConsoleObserver

class OutputManager:
    """输出管理器"""
    
    _observers = []
    
    @classmethod
    def add_observer(cls, observer: OutputObserver) -> None:
        cls._observers.append(observer)
    
    @classmethod
    def output_results(cls, results: Dict[str, Any]) -> None:
        """输出结果"""
        # 如果没有观察者，添加默认的控制台观察者
        if not cls._observers:
            cls.add_observer(ConsoleObserver())
            
        for observer in cls._observers:
            observer.on_output(results) 