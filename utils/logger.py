import os
import logging
import traceback
from logging.handlers import RotatingFileHandler
from typing import Optional

class Logger:
    """日志管理器"""
    
    _loggers = {}
    _default_level = logging.DEBUG
    _default_format = '%(asctime)s [%(levelname)s] %(message)s'
    _default_log_dir = 'logs'
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取或创建日志器"""
        if name not in cls._loggers:
            cls._loggers[name] = cls._create_logger(name)
        return cls._loggers[name]
    
    @classmethod
    def _create_logger(cls, name: str) -> logging.Logger:
        """创建日志器"""
        logger = logging.getLogger(name)
        
        # 设置日志器级别
        logger.setLevel(cls._default_level)
        
        # 如果已经有处理器，不重复添加
        if logger.handlers:
            return logger
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(cls._default_level)
        console_handler.setFormatter(logging.Formatter(cls._default_format))
        logger.addHandler(console_handler)
        
        # 创建文件处理器
        file_handler = cls._create_file_handler(name)
        if file_handler:
            file_handler.setLevel(cls._default_level)
            logger.addHandler(file_handler)
        
        # 重写error方法以包含堆栈跟踪
        def error_with_stack(msg, *args, **kwargs):
            stack_trace = traceback.format_exc()
            if stack_trace != "NoneType: None\n":  # 如果有异常堆栈
                msg = f"{msg}\n堆栈跟踪:\n{stack_trace}"
            logger.log(logging.ERROR, msg, *args, **kwargs)
        
        # 保存原始error方法
        logger._original_error = logger.error
        # 替换error方法
        logger.error = error_with_stack
        
        return logger
    
    @classmethod
    def _create_file_handler(cls, name: str) -> Optional[RotatingFileHandler]:
        """创建文件处理器"""
        try:
            # 确保日志目录存在
            if not os.path.exists(cls._default_log_dir):
                os.makedirs(cls._default_log_dir)
            
            # 创建文件处理器
            log_file = os.path.join(cls._default_log_dir, f'{name}.log')
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(cls._default_level)
            file_handler.setFormatter(logging.Formatter(cls._default_format))
            return file_handler
            
        except Exception as e:
            print(f"创建文件处理器失败: {str(e)}")
            return None
    
    @classmethod
    def set_level(cls, level: int) -> None:
        """设置日志级别"""
        cls._default_level = level
        # 更新所有已存在的日志器和处理器的级别
        for logger in cls._loggers.values():
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)
    
    @classmethod
    def set_format(cls, format_str: str) -> None:
        """设置日志格式"""
        cls._default_format = format_str
        formatter = logging.Formatter(format_str)
        for logger in cls._loggers.values():
            for handler in logger.handlers:
                handler.setFormatter(formatter)