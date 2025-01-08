from abc import ABC, abstractmethod
from typing import Dict, Any, Set
from utils.event_bus import EventBus
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class ResultHandler(ABC):
    """结果处理器基类"""
    
    def __init__(self):
        self.event_bus = EventBus.get_instance()
        self.subscribed_events: Set[str] = set()
        self._register_handlers()
    
    @abstractmethod
    def _register_handlers(self) -> None:
        """注册事件处理器"""
        pass
    
    def subscribe(self, event_type: str, handler) -> None:
        """订阅事件"""
        try:
            self.event_bus.subscribe(event_type, handler)
            self.subscribed_events.add(event_type)
            logger.debug(f"{self.__class__.__name__} 订阅事件: {event_type}")
        except Exception as e:
            logger.error(f"订阅事件失败: {str(e)}")
    
    def unsubscribe_all(self) -> None:
        """取消所有订阅"""
        try:
            for event_type in self.subscribed_events:
                for handler in self.__class__.__dict__.values():
                    if callable(handler) and hasattr(handler, '__name__'):
                        if handler.__name__.startswith('handle_'):
                            self.event_bus.unsubscribe(event_type, handler.__get__(self, self.__class__))
            self.subscribed_events.clear()
            logger.debug(f"{self.__class__.__name__} 取消所有订阅")
        except Exception as e:
            logger.error(f"取消订阅失败: {str(e)}") 