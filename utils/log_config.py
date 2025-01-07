import os
import logging
from logging.handlers import RotatingFileHandler
import sys
from datetime import datetime
from pathlib import Path

# 日志格式
DETAILED_FORMAT = '%(asctime)s [%(levelname)s] %(name)s:%(filename)s:%(lineno)d:%(funcName)s - %(message)s'
SIMPLE_FORMAT = '%(asctime)s [%(levelname)s] %(message)s'

# 日志级别映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

class LogConfig:
    """日志配置类"""
    
    # 默认配置
    DEFAULT_LOG_LEVEL = 'INFO'
    MAX_BYTES = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT = 5
    
    @classmethod
    def setup_logging(cls, 
                     log_level: str = None,
                     log_dir: str = None) -> None:
        """
        设置日志配置
        
        Args:
            log_level: 日志级别
            log_dir: 日志目录
        """
        # 获取日志级别
        log_level = log_level or os.getenv('LOG_LEVEL', cls.DEFAULT_LOG_LEVEL)
        level = LOG_LEVELS.get(log_level.upper(), logging.INFO)
        
        # 创建日志目录
        log_dir = Path(log_dir or 'logs')
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # 清除现有处理器
        root_logger.handlers.clear()
        
        # 1. 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(SIMPLE_FORMAT))
        root_logger.addHandler(console_handler)
        
        # 2. 文件处理器 - 所有日志
        all_handler = RotatingFileHandler(
            filename=log_dir / 'all.log',
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        all_handler.setLevel(level)
        all_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
        root_logger.addHandler(all_handler)
        
        # 3. 文件处理器 - 错误日志
        error_handler = RotatingFileHandler(
            filename=log_dir / 'error.log',
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(DETAILED_FORMAT))
        root_logger.addHandler(error_handler)

class ErrorLogFilter(logging.Filter):
    """错误日志过滤器"""
    def filter(self, record):
        return record.levelno >= logging.ERROR 