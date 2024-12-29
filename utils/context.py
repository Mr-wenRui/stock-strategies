from typing import Dict, Any, Optional
import yaml
from pathlib import Path
import threading
import logging

class SystemContext:
    """
    系统上下文
    管理系统级的配置和公共数据
    使用单例模式确保全局唯一
    """
    
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._config = {}
                    self._cache = {}
                    self._initialized = True
                    
    def _get_root_path(self) -> str:
        current_file_path = Path(__file__).resolve()
        root_path = current_file_path.parents[1]  # 获取当前目录的上两级
        return root_path
    
    @property
    def config(self) -> Dict:
        """获取系统配置"""
        return self._config
    
    def init_config(self, config_path: Optional[str] = None) -> None:
        """初始化系统配置"""
        try:
            if config_path is None:
                config_path = Path(self._get_root_path(), "config/application.yaml")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
                
            logging.info("系统配置加载成功")
            
        except Exception as e:
            logging.error(f"加载系统配置失败: {str(e)}")
            raise
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        支持使用点号访问嵌套配置
        
        Args:
            key: 配置键，如 'redis.host'
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            value = self._config
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_cache(self, key: str, value: Any) -> None:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        with self._lock:
            self._cache[key] = value
    
    def get_cache(self, key: str, default: Any = None) -> Any:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            缓存值
        """
        return self._cache.get(key, default)
    
    def clear_cache(self, key: Optional[str] = None) -> None:
        """
        清除缓存数据
        
        Args:
            key: 缓存键，如果为None则清除所有缓存
        """
        with self._lock:
            if key is None:
                self._cache.clear()
            else:
                self._cache.pop(key, None)
    
    @property
    def redis_config(self) -> Dict:
        """获取Redis配置"""
        return self.get_config('redis', {})
    
    @property
    def kafka_config(self) -> Dict:
        """获取Kafka配置"""
        return self.get_config('kafka', {})
    
    @property
    def clickhouse_config(self) -> Dict:
        """获取ClickHouse配置"""
        return self.get_config('clickhouse', {})

# 全局上下文实例
context = SystemContext() 