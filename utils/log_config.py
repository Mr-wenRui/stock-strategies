import logging
from .logger import Logger


class LogConfig:
    """日志配置"""
    
    @staticmethod
    def setup_logging(log_level: str = 'INFO', log_dir: str = 'logs') -> None:
        """设置日志配置"""
        # 设置日志目录
        Logger._default_log_dir = log_dir
        
        # 设置日志级别
        level = getattr(logging, log_level.upper(), logging.INFO)
        Logger.set_level(level)
        
        # 设置根日志器级别
        logging.getLogger().setLevel(level) 