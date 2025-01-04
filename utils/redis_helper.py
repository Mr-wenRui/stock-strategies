import redis
import pandas as pd
import numpy as np
import pickle
import json
from typing import Union, Optional, Any, List, Callable
from datetime import datetime
from functools import wraps
from utils.config import Config
import logging

logger = logging.getLogger(__name__)

def redis_client(func: Callable):
    """Redis客户端连接池装饰器"""
    @wraps(func)
    def wrapper(cls, *args, **kwargs):
        client = RedisHelper._get_client()
        try:
            return func(cls, client, *args, **kwargs)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            # 连接错误时尝试重新获取连接
            RedisHelper._client = None
            client = RedisHelper._get_client()
            return func(cls, client, *args, **kwargs)
    return wrapper

class RedisHelper:
    """Redis数据读取工具类，专注于高性能DataFrame处理"""
    
    _client = None
    _pool = None
    
    @classmethod
    def _get_client(cls) -> redis.Redis:
        """获取Redis客户端（使用连接池）"""
        if cls._client is None:
            if cls._pool is None:
                config = Config.get_config('redis')
                if not config:
                    raise ValueError("Redis configuration not found")
                    
                cls._pool = redis.ConnectionPool(
                    host=config.get('host', 'localhost'),
                    port=config.get('port', 6379),
                    db=config.get('db', 0),
                    password=config.get('password', None),
                    decode_responses=False,
                    socket_timeout=config.get('socket_timeout', 5),
                    socket_connect_timeout=config.get('socket_connect_timeout', 5),
                    socket_keepalive=True,
                    health_check_interval=config.get('health_check_interval', 30),
                    max_connections=config.get('max_connections', 100),
                    retry_on_timeout=True
                )
            cls._client = redis.Redis(connection_pool=cls._pool)
        return cls._client

    @classmethod
    @redis_client
    def get_df(cls, client: redis.Redis, key: str) -> pd.DataFrame:
        """
        获取DataFrame数据
        支持两种格式：
        1. pickle序列化的DataFrame
        2. JSON格式的DataFrame数据
        """
        try:
            data = client.get(key)
            if data is None:
                logger.warning(f"Redis key '{key}' 不存在")
                return pd.DataFrame()
            
            # 首先尝试JSON格式解析
            try:
                # 解码为字符串（JSON格式存储时通常是字符串）
                json_str = data.decode('utf-8')
                json_data = json.loads(json_str)
                
                # 检查是否是预期的JSON格式
                if isinstance(json_data, dict) and all(k in json_data for k in ['data', 'columns']):
                    df = pd.DataFrame(
                        data=json_data['data'],
                        columns=json_data['columns']
                    )
                    # 如果存在索引数据，设置索引
                    if 'index' in json_data:
                        df.index = json_data['index']
                    return df
                    
            except (UnicodeDecodeError, json.JSONDecodeError):
                # 如果不是JSON格式，尝试pickle格式
                try:
                    df = pickle.loads(data)
                    if isinstance(df, pd.DataFrame):
                        return df
                except Exception as e:
                    logger.error(f"反序列化DataFrame失败: {str(e)}")
                    
            except Exception as e:
                logger.error(f"解析JSON格式DataFrame失败: {str(e)}")
                
            logger.warning(f"Redis key '{key}' 的数据格式无法识别")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"从Redis获取数据失败: {str(e)}")
            return pd.DataFrame()

    @classmethod
    @redis_client
    def set_df(cls, client: redis.Redis, key: str, df: pd.DataFrame, expire: Optional[int] = None, use_json: bool = True) -> bool:
        """
        存储DataFrame数据
        
        Args:
            key: Redis键
            df: DataFrame对象
            expire: 过期时间（秒）
            use_json: 是否使用JSON格式存储（默认True）
        """
        try:
            if not isinstance(df, pd.DataFrame):
                logger.error("输入数据不是DataFrame类型")
                return False
            
            if use_json:
                # 使用JSON格式存储
                json_data = {
                    'data': df.to_dict(orient='records'),
                    'columns': df.columns.tolist(),
                    'index': df.index.tolist()
                }
                data = json.dumps(json_data)
                client.set(key, data)
            else:
                # 使用pickle格式存储
                data = pickle.dumps(df)
                client.set(key, data)
                
            if expire:
                client.expire(key, expire)
            return True
            
        except Exception as e:
            logger.error(f"存储DataFrame到Redis失败: {str(e)}")
            return False

    @classmethod
    @redis_client
    def get_array(cls, client: redis.Redis, key: str) -> np.ndarray:
        """获取numpy数组数据"""
        data = client.get(key)
        if data is None:
            return np.array([])
        return pickle.loads(data)

    @classmethod
    @redis_client
    def set_array(cls, client: redis.Redis, key: str, arr: np.ndarray, expire: Optional[int] = None) -> None:
        """存储numpy数组数据"""
        data = pickle.dumps(arr)
        client.set(key, data)
        if expire:
            client.expire(key, expire)

    @classmethod
    @redis_client
    def get_list(cls, client: redis.Redis, key: str) -> List:
        """获取列表数据"""
        try:
            data = client.get(key)
            if data is None:
                logger.warning(f"Redis key '{key}' 不存在")
                return []
            
            # 尝试反序列化
            try:
                lst = pickle.loads(data)
                if isinstance(lst, list):
                    return lst
                logger.warning(f"Redis key '{key}' 的数据不是List格式")
                return []
            except Exception as e:
                logger.error(f"反序列化List失败: {str(e)}")
                return []
            
        except Exception as e:
            logger.error(f"从Redis获取数据失败: {str(e)}")
            return []

    @classmethod
    @redis_client
    def set_list(cls, client: redis.Redis, key: str, data_list: List, expire: Optional[int] = None) -> bool:
        """存储列表数据"""
        try:
            if not isinstance(data_list, list):
                logger.error("输入数据不是List类型")
                return False
            
            data = pickle.dumps(data_list)
            client.set(key, data)
            if expire:
                client.expire(key, expire)
            return True
        except Exception as e:
            logger.error(f"存储List到Redis失败: {str(e)}")
            return False

    @classmethod
    @redis_client
    def get_dict(cls, client: redis.Redis, key: str) -> dict:
        """获取字典数据"""
        data = client.get(key)
        if data is None:
            return {}
        return pickle.loads(data)

    @classmethod
    @redis_client
    def set_dict(cls, client: redis.Redis, key: str, data_dict: dict, expire: Optional[int] = None) -> None:
        """存储字典数据"""
        data = pickle.dumps(data_dict)
        client.set(key, data)
        if expire:
            client.expire(key, expire)

    @classmethod
    @redis_client
    def exists(cls, client: redis.Redis, key: str) -> bool:
        """检查键是否存在"""
        return bool(client.exists(key))

    @classmethod
    @redis_client
    def delete(cls, client: redis.Redis, key: str) -> bool:
        """删除键"""
        return bool(client.delete(key))

    @classmethod
    @redis_client
    def get_ttl(cls, client: redis.Redis, key: str) -> int:
        """获取键的剩余过期时间（秒）"""
        return client.ttl(key)

    @classmethod
    @redis_client
    def set_expire(cls, client: redis.Redis, key: str, seconds: int) -> bool:
        """设置过期时间"""
        return bool(client.expire(key, seconds))

    @classmethod
    @redis_client
    def clear_expire(cls, client: redis.Redis, key: str) -> bool:
        """清除过期时间"""
        return bool(client.persist(key)) 