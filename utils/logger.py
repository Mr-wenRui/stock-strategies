import logging
import logging.config
import yaml
from pathlib import Path
from typing import Optional
from utils.uitl import get_root_path


class Logger:
    """日志管理器"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not Logger._initialized:
            self._setup_logging()
            Logger._initialized = True
    
    def _get_default_config(self) -> dict:
        """获取默认日志配置"""
        return {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': '%(asctime)s [%(levelname)s] %(pathname)s:%(lineno)d:%(funcName)s - %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': 'DEBUG',
                    'formatter': 'standard',
                    'stream': 'ext://sys.stdout'
                },
                'file': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'INFO',
                    'formatter': 'standard',
                    'filename': 'logs/app.log',
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': 5,
                    'encoding': 'utf8'
                }
            },
            'loggers': {
                '': {  # root logger
                    'level': 'INFO',
                    'handlers': ['console', 'file'],
                    'propagate': True
                }
            }
        }
    
    def _setup_logging(self, config_path: str = 'config/logging.yaml', default_level=logging.INFO):
        """初始化日志配置"""
        try:
            # 确保logs目录存在
            Path('logs').mkdir(exist_ok=True)
            
            # 加载配置
            config = None
            if Path(get_root_path(), config_path).exists():
                with open(config_path, 'rt', encoding='utf8') as f:
                    config = yaml.safe_load(f)
            
            # 如果配置文件不存在或加载失败，使用默认配置
            if not config:
                config = self._get_default_config()
            
            # 应用日志配置
            logging.config.dictConfig(config)
            
        except Exception as e:
            # 配置失败时使用基础配置
            default_config = self._get_default_config()
            logging.config.dictConfig(default_config)
            logging.error(f"加载日志配置失败: {str(e)}")
    
    @staticmethod
    def get_logger(name: Optional[str] = None) -> logging.Logger:
        """获取日志记录器"""
        Logger()  # 确保已初始化
        return logging.getLogger(name)