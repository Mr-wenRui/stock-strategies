from typing import Optional, Any, List, Dict, Union
import redis
from redis.connection import ConnectionPool
import yaml
import json
import pandas as pd
from utils.context import context

from utils.logger import Logger
logger = Logger.get_logger(__name__)

class RedisClient:
    """
    Redis 工具类
    提供常用的 Redis 操作方法，使用连接池管理连接
    所有配置从 config/application.yaml 读取
    
    Attributes:
        _pool: Redis连接池实例
    """
    
    _pool = None

    @staticmethod
    def _get_pool() -> ConnectionPool:
        """
        获取或创建Redis连接池
        
        Returns:
            ConnectionPool: Redis连接池实例
        
        Raises:
            Exception: 配置文件读取失败或连接池创建失败时抛出异常
        """
        if RedisClient._pool is None:
            try:
                # 从上下文获取配置
                redis_config = context.redis_config
                pool_config = context.get_config('redis_pool', {})
                
                RedisClient._pool = ConnectionPool(
                    host=redis_config.get('host', 'localhost'),
                    port=redis_config.get('port', 6379),
                    password=redis_config.get('password', ''),
                    db=redis_config.get('db', 0),
                    decode_responses=True,
                    max_connections=pool_config.get('max_connections', 10),
                    socket_timeout=pool_config.get('socket_timeout', 30),
                    socket_connect_timeout=pool_config.get('connect_timeout', 10),
                    socket_keepalive=True,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                logger.info("Redis连接池初始化成功")
            except Exception as e:
                logger.error(f"初始化Redis连接池失败: {str(e)}")
                raise
        return RedisClient._pool

    @staticmethod
    def _get_connection() -> redis.Redis:
        """
        从连接池获取Redis连接
        
        Returns:
            redis.Redis: Redis客户端实例
        """
        return redis.Redis(connection_pool=RedisClient._get_pool())

    @staticmethod
    def set_value(key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        设置键值对
        
        Args:
            key: 键名
            value: 值（支持Python基本类型和复杂对象，会自动序列化）
            expire: 过期时间（秒），可选
            
        Returns:
            bool: 操作是否成功
            
        Examples:
            >>> RedisClient.set_value("key1", "value1")
            True
            >>> RedisClient.set_value("key2", {"name": "test"}, expire=3600)
            True
        """
        try:
            client = RedisClient._get_connection()
            pipeline = client.pipeline()
            
            # 序列化值
            if not isinstance(value, (str, int, float)):
                value = json.dumps(value)
                
            # 添加命令到管道
            pipeline.set(key, value)
            if expire:
                pipeline.expire(key, expire)
                
            # 执行管道中的所有命令
            pipeline.execute()
            return True
            
        except Exception as e:
            logger.error(f"设置Redis键 {key} 失败: {str(e)}")
            return False

    @staticmethod
    def get_value(key: str, default: Any = None) -> Any:
        """
        获取值
        
        Args:
            key: 键
            default: 默认值
            
        Returns:
            解析后的值
        """
        try:
            client = RedisClient._get_connection()
            value = client.get(key)
            if value is None:
                return default
            # 尝试解析 JSON
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value
        except Exception as e:
            logger.error(f"Failed to get Redis key {key}: {str(e)}")
            return default

    @staticmethod
    def delete_key(key: str) -> bool:
        """
        删除键
        
        Args:
            key: 键
            
        Returns:
            bool: 操作是否成功
        """
        try:
            client = RedisClient._get_connection()
            return bool(client.delete(key))
        except Exception as e:
            logger.error(f"Failed to delete Redis key {key}: {str(e)}")
            return False

    @staticmethod
    def exists_key(key: str) -> bool:
        """
        检查键是否存在
        
        Args:
            key: 键
            
        Returns:
            bool: 键是否存在
        """
        try:
            client = RedisClient._get_connection()
            return bool(client.exists(key))
        except Exception as e:
            logger.error(f"Failed to check Redis key {key}: {str(e)}")
            return False

    @staticmethod
    def set_expire(key: str, expire: int) -> bool:
        """
        设置过期时间
        
        Args:
            key: 键
            expire: 过期时间（秒）
            
        Returns:
            bool: 操作是否成功
        """
        try:
            client = RedisClient._get_connection()
            return bool(client.expire(key, expire))
        except Exception as e:
            logger.error(f"Failed to set expire for Redis key {key}: {str(e)}")
            return False

    @staticmethod
    def get_ttl(key: str) -> int:
        """
        获取键的剩余生存时间
        
        Args:
            key: 键
            
        Returns:
            int: 剩余秒数，-1表示永久，-2表示不存在
        """
        try:
            client = RedisClient._get_connection()
            return client.ttl(key)
        except Exception as e:
            logger.error(f"Failed to get TTL for Redis key {key}: {str(e)}")
            return -2

    @staticmethod
    def incr(key: str, amount: int = 1) -> Optional[int]:
        """
        递增
        
        Args:
            key: 键
            amount: 增加量
            
        Returns:
            Optional[int]: 增加后的值
        """
        try:
            client = RedisClient._get_connection()
            return client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Failed to increment Redis key {key}: {str(e)}")
            return None

    @staticmethod
    def hash_set(name: str, key: str, value: Any) -> bool:
        """
        设置哈希表字段
        
        Args:
            name: 哈希表名
            key: 字段名
            value: 值
            
        Returns:
            bool: 操作是否成功
        """
        try:
            client = RedisClient._get_connection()
            if not isinstance(value, (str, int, float)):
                value = json.dumps(value)
            return bool(client.hset(name, key, value))
        except Exception as e:
            logger.error(f"Failed to set hash field {name}:{key}: {str(e)}")
            return False

    @staticmethod
    def hash_get(name: str, key: str, default: Any = None) -> Any:
        """
        获取哈希表字段
        
        Args:
            name: 哈希表名
            key: 字段名
            default: 默认值
            
        Returns:
            解析后的值
        """
        try:
            client = RedisClient._get_connection()
            value = client.hget(name, key)
            if value is None:
                return default
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value
        except Exception as e:
            logger.error(f"Failed to get hash field {name}:{key}: {str(e)}")
            return default

    @staticmethod
    def hash_getall(name: str) -> Dict:
        """
        获取哈希表所有字段
        
        Args:
            name: 哈希表名
            
        Returns:
            Dict: 字段名和值的映射
        """
        try:
            client = RedisClient._get_connection()
            return client.hgetall(name)
        except Exception as e:
            logger.error(f"Failed to get all hash fields for {name}: {str(e)}")
            return {}

    @staticmethod
    def list_push(name: str, *values: Any) -> Optional[int]:
        """
        将一个或多个值插入到列表头部
        
        Args:
            name: 列表名
            *values: 要插入的值
            
        Returns:
            Optional[int]: 操作后列表长度
        """
        try:
            client = RedisClient._get_connection()
            serialized_values = [
                json.dumps(v) if not isinstance(v, (str, int, float)) else v
                for v in values
            ]
            return client.lpush(name, *serialized_values)
        except Exception as e:
            logger.error(f"Failed to push to list {name}: {str(e)}")
            return None

    @staticmethod
    def list_range(name: str, start: int = 0, end: int = -1) -> List:
        """
        获取列表指定范围内的元素
        
        Args:
            name: 列表名
            start: 开始位置
            end: 结束位置
            
        Returns:
            List: 指定范围内的元素
        """
        try:
            client = RedisClient._get_connection()
            values = client.lrange(name, start, end)
            return [
                json.loads(v) if v.startswith('{') or v.startswith('[') else v
                for v in values
            ]
        except Exception as e:
            logger.error(f"Failed to get range from list {name}: {str(e)}")
            return []

    @staticmethod
    def close_pool():
        """
        关闭连接池
        在程序结束时调用，确保资源正确释放
        
        Examples:
            >>> RedisClient.close_pool()
        """
        if RedisClient._pool is not None:
            RedisClient._pool.disconnect()
            RedisClient._pool = None
            logger.info("Redis连接池已关闭")

    @staticmethod
    def set_df(name: str, df: pd.DataFrame, expire: Optional[int] = None) -> bool:
        """
        将 DataFrame 存储到 Redis
        使用 JSON 格式存储，支持过期时间
        
        Args:
            name: 键名
            df: 要存储的 DataFrame
            expire: 过期时间（秒），可选
            
        Returns:
            bool: 操作是否成功
            
        Examples:
            >>> df = pd.DataFrame({'A': [1, 2], 'B': ['a', 'b']})
            >>> RedisClient.set_df('my_df', df, expire=3600)
            True
        """
        try:
            # 转换 DataFrame 为 JSON
            json_data = {
                'data': df.to_dict(orient='records'),
                'columns': df.columns.tolist(),
                'index': df.index.tolist()
            }
            return RedisClient.set_value(name, json_data, expire)
        except Exception as e:
            logger.error(f"Failed to store DataFrame: {str(e)}")
            return False

    @staticmethod
    def get_df(name: str) -> Optional[pd.DataFrame]:
        """
        从 Redis 获取 DataFrame
        
        Args:
            name: 键名
            
        Returns:
            Optional[pd.DataFrame]: 获取的 DataFrame，失败返回 None
            
        Examples:
            >>> df = RedisClient.get_df('my_df')
            >>> print(df)
               A  B
            0  1  a
            1  2  b
        """
        try:
            json_data = RedisClient.get_value(name)
            if json_data and isinstance(json_data, dict):
                df = pd.DataFrame(json_data['data'])
                # 恢复列顺序
                df = df[json_data['columns']]
                # 恢复索引
                df.index = json_data['index']
                return df
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve DataFrame: {str(e)}")
            return None

    @staticmethod
    def publish(channel: str, message: Any) -> bool:
        """
        发布消息到指定频道
        
        Args:
            channel: 频道名
            message: 消息内容（支持Python对象，会自动序列化）
            
        Returns:
            bool: 操作是否成功
            
        Examples:
            >>> RedisClient.publish('notifications', {'event': 'update', 'id': 123})
            True
        """
        try:
            client = RedisClient._get_connection()
            if not isinstance(message, (str, int, float)):
                message = json.dumps(message)
            return bool(client.publish(channel, message))
        except Exception as e:
            logger.error(f"Failed to publish message to {channel}: {str(e)}")
            return False

    @staticmethod
    def set_bit(key: str, offset: int, value: bool) -> bool:
        """
        设置位图的某一位
        常用于用户签到、在线状态等场景
        
        Args:
            key: 键名
            offset: 位偏移量
            value: 位的值
            
        Returns:
            bool: 操作是否成功
            
        Examples:
            >>> RedisClient.set_bit('user:login:2024-01-01', user_id, True)  # 记录用户登录
            True
        """
        try:
            client = RedisClient._get_connection()
            client.setbit(key, offset, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set bit: {str(e)}")
            return False

    @staticmethod
    def get_bit(key: str, offset: int) -> bool:
        """
        获取位图的某一位
        
        Args:
            key: 键名
            offset: 位偏移量
            
        Returns:
            bool: 位的值
            
        Examples:
            >>> is_logged = RedisClient.get_bit('user:login:2024-01-01', user_id)
            >>> print(is_logged)
            True
        """
        try:
            client = RedisClient._get_connection()
            return bool(client.getbit(key, offset))
        except Exception as e:
            logger.error(f"Failed to get bit: {str(e)}")
            return False

    @staticmethod
    def zadd(name: str, mapping: Dict[str, float]) -> bool:
        """
        向有序集合添加元素
        常用于排行榜等场景
        
        Args:
            name: 有序集合名
            mapping: 成员和分数的映射
            
        Returns:
            bool: 操作是否成功
            
        Examples:
            >>> RedisClient.zadd('highscores', {'player1': 100, 'player2': 200})
            True
        """
        try:
            client = RedisClient._get_connection()
            client.zadd(name, mapping)
            return True
        except Exception as e:
            logger.error(f"Failed to add to sorted set: {str(e)}")
            return False

    @staticmethod
    def zrange(name: str, start: int = 0, end: int = -1, 
               withscores: bool = False, desc: bool = False) -> Union[List, List[tuple]]:
        """
        获取有序集合的范围
        
        Args:
            name: 有序集合名
            start: 起始位置
            end: 结束位置
            withscores: 是否返回分数
            desc: 是否按分数降序排序
            
        Returns:
            Union[List, List[tuple]]: 成员列表或(成员,分数)元组列表
            
        Examples:
            >>> scores = RedisClient.zrange('highscores', 0, 2, withscores=True, desc=True)
            >>> print(scores)
            [('player2', 200.0), ('player1', 100.0)]
        """
        try:
            client = RedisClient._get_connection()
            return client.zrange(name, start, end, withscores=withscores, desc=desc)
        except Exception as e:
            logger.error(f"Failed to get range from sorted set: {str(e)}")
            return []

    @staticmethod
    def pipeline() -> redis.client.Pipeline:
        """
        获取 Redis 管道对象，用于批量操作
        
        Returns:
            redis.client.Pipeline: Redis管道对象
            
        Examples:
            >>> with RedisClient.pipeline() as pipe:
            ...     pipe.set('key1', 'value1')
            ...     pipe.set('key2', 'value2')
            ...     pipe.execute()
        """
        client = RedisClient._get_connection()
        return client.pipeline()

    @staticmethod
    def scan_keys(pattern: str) -> List[str]:
        """
        使用 scan 命令查找匹配的键
        
        Args:
            pattern: 匹配模式（如：'user:*'）
            
        Returns:
            List[str]: 匹配的键列表
            
        Examples:
            >>> keys = RedisClient.scan_keys('stock:daily:*')
            >>> print(keys)
            ['stock:daily:600519', 'stock:daily:000001']
        """
        try:
            client = RedisClient._get_connection()
            keys = []
            cursor = 0
            while True:
                cursor, partial_keys = client.scan(
                    cursor=cursor,
                    match=pattern,
                    count=1000  # 每次扫描的数量
                )
                keys.extend(partial_keys)
                if cursor == 0:  # 扫描完成
                    break
            return keys
        except Exception as e:
            logger.error(f"Failed to scan keys with pattern {pattern}: {str(e)}")
            return []
    @staticmethod
    def health_check() -> Dict[str, Any]:
        """
        Redis健康检查
        检查连接状态和基本信息

        Returns:
            Dict: 包含健康状态和详细信息的字典
            {
                'status': 'healthy' | 'unhealthy',
                'connection': True | False,
                'total_keys': int,
                'used_memory_human': str,
                'used_memory_peak_human': str,
                'connected_clients': int,
                'uptime_days': int,
                'error': str (可选，当status为unhealthy时)
            }
        """
        try:
            client = RedisClient._get_connection()
            info = client.info()
            
            # 获取所有键的数量
            db_keys = 0
            for db in range(16):  # 检查所有数据库
                try:
                    db_info = client.info(section=f"db{db}")
                    if db_info:
                        db_keys += db_info.get(f"db{db}", {}).get("keys", 0)
                except:
                    continue

            return {
                'status': 'healthy',
                'connection': True,
                'total_keys': db_keys,
                'used_memory_human': info.get('used_memory_human', 'N/A'),
                'used_memory_peak_human': info.get('used_memory_peak_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0),
                'uptime_days': info.get('uptime_in_days', 0),
                'version': info.get('redis_version', 'N/A'),
                'stock_cache_keys': len(RedisClient.scan_keys("stock:*"))
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'connection': False,
                'error': str(e)
            }