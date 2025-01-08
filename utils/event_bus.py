from typing import Dict, List, Any, Callable, Optional
from collections import defaultdict
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class EventBus:
    """事件总线"""
    _instance: Optional['EventBus'] = None
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
    
    @classmethod
    def get_instance(cls) -> 'EventBus':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """订阅事件"""
        try:
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
                logger.debug(f"订阅事件 {event_type}: {callback.__name__}")
        except Exception as e:
            logger.error(f"订阅事件失败: {str(e)}")
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """取消订阅"""
        try:
            if event_type in self._subscribers:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"取消订阅事件 {event_type}: {callback.__name__}")
        except Exception as e:
            logger.error(f"取消订阅事件失败: {str(e)}")
    
    def publish(self, event_type: str, data: Any = None) -> None:
        """发布事件"""
        try:
            for callback in self._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"事件处理失败 {event_type}: {str(e)}")
        except Exception as e:
            logger.error(f"发布事件失败 {event_type}: {str(e)}")
    
    def clear(self) -> None:
        """清除所有订阅"""
        try:
            self._subscribers.clear()
            logger.debug("清除所有事件订阅")
        except Exception as e:
            logger.error(f"清除事件订阅失败: {str(e)}") 