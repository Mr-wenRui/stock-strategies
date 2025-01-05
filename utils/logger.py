import os
import logging
import logging.config
import yaml
from typing import Optional
import traceback

class Logger:
    """日志管理器"""
    
    _initialized = False
    
    @classmethod
    def initialize(cls) -> None:
        """初始化日志系统"""
        if cls._initialized:
            return
            
        try:
            # 确保日志目录存在
            os.makedirs('logs', exist_ok=True)
            
            # 加载日志配置
            config_path = 'config/logging.yaml'
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    logging.config.dictConfig(config)
                    
                # 输出初始化成功信息
                root_logger = logging.getLogger()
                root_logger.debug("日志系统初始化成功")
            else:
                print(f"未找到日志配置文件: {config_path}")
                cls._setup_basic_config()
            
            cls._initialized = True
            
        except Exception as e:
            print(f"初始化日志系统失败: {str(e)}")
            cls._setup_basic_config()
    
    @classmethod
    def _setup_basic_config(cls):
        """设置基本日志配置"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d:%(funcName)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('logs/backtest.log', encoding='utf8')
            ]
        )
    
    @classmethod
    def get_logger(cls, name: Optional[str] = None) -> logging.Logger:
        """获取日志记录器"""
        if not cls._initialized:
            cls.initialize()
        
        logger = logging.getLogger(name)
        
        # 确保至少有一个处理器
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler())
        
        # 添加错误日志增强
        original_error = logger.error
        def error_with_stack(msg, *args, **kwargs):
            if not kwargs.get('exc_info'):
                stack_trace = traceback.format_exc()
                if stack_trace != "NoneType: None\n":
                    msg = f"{msg}\nStack trace:\n{stack_trace}"
            original_error(msg, *args, **kwargs)
        logger.error = error_with_stack
        
        return logger

    @classmethod
    def test_logging(cls):
        """测试日志功能"""
        logger = cls.get_logger("test")
        logger.debug("这是一条调试日志")
        logger.info("这是一条信息日志")
        logger.warning("这是一条警告日志")
        try:
            raise ValueError("测试错误")
        except Exception as e:
            logger.error(f"这是一条错误日志: {str(e)}")