import logging
import traceback
from functools import wraps
from typing import Callable, Any

class Logger:
    """日志工具类"""
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """获取日志记录器"""
        return logging.getLogger(name)
    
    @staticmethod
    def debug_with_stack(logger: logging.Logger, message: str) -> None:
        """带堆栈的调试日志"""
        logger.debug(f"{message}\nStack trace:\n{traceback.format_stack()}")
    
    @staticmethod
    def error_with_stack(logger: logging.Logger, message: str) -> None:
        """带堆栈的错误日志"""
        logger.error(f"{message}\nStack trace:\n{traceback.format_exc()}")
    
    @staticmethod
    def log_execution(logger: logging.Logger) -> Callable:
        """函数执行日志装饰器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                try:
                    logger.debug(f"开始执行 {func.__name__}")
                    result = func(*args, **kwargs)
                    logger.debug(f"完成执行 {func.__name__}")
                    return result
                except Exception as e:
                    Logger.error_with_stack(logger, f"执行 {func.__name__} 失败: {str(e)}")
                    raise
            return wrapper
        return decorator