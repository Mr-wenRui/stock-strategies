import os
import yaml
from typing import Dict, Any

class Config:
    """配置管理类"""
    
    _instance = None
    _config = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def load_config(cls, config_path: str = None) -> None:
        """加载配置文件"""
        if not config_path:
            # 默认配置文件路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, 'config', 'application.yaml')
            
        with open(config_path, 'r', encoding='utf-8') as f:
            cls._config = yaml.safe_load(f)
    
    @classmethod
    def get_config(cls, key: str = None) -> Any:
        """获取配置"""
        if not cls._config:
            cls.load_config()
        if key:
            return cls._config.get(key)
        return cls._config 