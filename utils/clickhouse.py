from typing import List, Dict, Union, Optional, Any
import pandas as pd
from datetime import datetime
from clickhouse_driver import Client, connect
from utils.uitl import get_root_path
from utils.logger import Logger
from pathlib import Path
from dbutils.pooled_db import PooledDB
from functools import wraps


from utils.context import context

logger = Logger.get_logger(__name__)

class ClickHouseClient:
    """
    ClickHouse 数据库操作工具类
    提供数据库连接管理和基本的增删改查操作
    使用连接池管理数据库连接
    """
    
    # 连接池实例
    _pool = None

    @classmethod
    def init_pool(cls):
        """初始化连接池"""
        if cls._pool is None:
            try:
                # 获取ClickHouse配置
                ch_config = context.clickhouse_config
                pool_config = context.get_config('clickhouse_pool', {})
                
                # 创建连接池
                cls._pool = PooledDB(
                    creator=connect,  # 使用 clickhouse_driver.connect
                    maxconnections=pool_config.get('max_connections', 10),
                    mincached=pool_config.get('min_cached', 2),
                    maxcached=pool_config.get('max_cached', 5),
                    maxshared=pool_config.get('max_shared', 3),
                    blocking=True,
                    maxusage=pool_config.get('max_usage', 0),
                    host=ch_config.get('host', 'localhost'),
                    port=ch_config.get('port', 9000),
                    user=ch_config.get('user', 'default'),
                    password=ch_config.get('password', ''),
                    database=ch_config.get('database', 'default'),
                    connect_timeout=10
                )
                logger.info("ClickHouse连接池初始化成功")
            except Exception as e:
                logger.error(f"初始化连接池失败: {str(e)}")
                raise

    @classmethod
    def get_connection(cls):
        """从连接池获取连接"""
        if cls._pool is None:
            cls.init_pool()
        return cls._pool.connection()

    @staticmethod
    def with_connection(func):
        """连接池管理装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            conn = None
            try:
                conn = ClickHouseClient.get_connection()
                return func(conn, *args, **kwargs)
            finally:
                if conn:
                    conn.close()
        return wrapper

    @staticmethod
    @with_connection
    def execute(conn, query: str, params: Optional[Dict] = None) -> None:
        """执行 SQL 查询"""
        cursor = conn.cursor()
        try:
            cursor.execute(query, params or {})
        except Exception as e:
            logger.error(f"执行ClickHouse查询失败: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()

    @staticmethod
    @with_connection
    def query_df(conn, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        """执行查询并返回 DataFrame"""
        cursor = conn.cursor()
        try:
            cursor.execute(query, params or {})
            columns = [col[0] for col in cursor.description]
            data = cursor.fetchall()
            return pd.DataFrame(data, columns=columns)
        except Exception as e:
            logger.error(f"查询DataFrame失败: {str(e)}\n查询语句: {query}")
            return pd.DataFrame()
        finally:
            if cursor:
                cursor.close()

    @staticmethod
    @with_connection
    def insert_df(conn, table: str, df: pd.DataFrame) -> None:
        """将DataFrame数据插入到ClickHouse表中"""
        try:
            if df.empty:
                logger.warning("DataFrame为空，跳过插入")
                return
                
            # 构建INSERT语句
            columns = ', '.join(df.columns)
            query = f"INSERT INTO {table} ({columns}) VALUES"
            
            # 直接使用DataFrame的values转换为列表
            data = df.values.tolist()
            
            # 执行插入
            cursor = conn.cursor()
            cursor.executemany(query, data)
            
            logger.info(f"成功插入 {len(df)} 条数据到表 {table}")
            
        except Exception as e:
            logger.error(f"插入数据到表 {table} 失败: {str(e)}")
            raise

    @staticmethod
    @with_connection
    def bulk_insert_df(conn, table: str, df: pd.DataFrame, batch_size: int = 50000) -> None:
        """批量插入大型 DataFrame"""
        total_rows = len(df)
        for i in range(0, total_rows, batch_size):
            batch_df = df.iloc[i:i + batch_size]
            ClickHouseClient.insert_df(conn, table, batch_df)
            logger.info(f"已插入第 {i//batch_size + 1} 批数据，进度: {min(i + batch_size, total_rows)}/{total_rows}")

    @staticmethod
    @with_connection
    def get_table_schema(conn, table: str) -> pd.DataFrame:
        """获取表结构信息"""
        return ClickHouseClient.query_df(conn, f"DESCRIBE {table}")

    @staticmethod
    @with_connection
    def get_table_count(conn, table: str, condition: str = "") -> int:
        """获取表中的记录数"""
        query = f"SELECT COUNT(*) as count FROM {table}"
        if condition:
            query += f" WHERE {condition}"
        result = ClickHouseClient.query_df(conn, query)
        return result['count'].iloc[0] if not result.empty else 0

    @staticmethod
    @with_connection
    def truncate_table(conn, table: str) -> None:
        """清空表数据"""
        ClickHouseClient.execute(conn, f"TRUNCATE TABLE {table}")
        logger.info(f"成功清空表 {table}")

    @staticmethod
    @with_connection
    def optimize_table(conn, table: str) -> None:
        """优化表"""
        ClickHouseClient.execute(conn, f"OPTIMIZE TABLE {table} FINAL")
        logger.info(f"成功优化表 {table}")

    @staticmethod
    def health_check() -> Dict[str, Any]:
        """ClickHouse健康检查"""
        cursor = None
        conn = None
        try:
            conn = ClickHouseClient.get_connection()
            cursor = conn.cursor()
            
            # 获取系统信息
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            
            # 获取数据库大小
            cursor.execute("""
                SELECT formatReadableSize(sum(bytes)) as size
                FROM system.parts
            """)
            db_size = cursor.fetchone()[0]
            
            # 获取服务器运行时间
            cursor.execute("SELECT uptime()")
            uptime = cursor.fetchone()[0]
            
            # 获取表信息
            cursor.execute("""
                SELECT 
                    table,
                    formatReadableSize(sum(bytes)) as size,
                    sum(rows) as total_rows,
                    max(modification_time) as last_modified
                FROM system.parts
                GROUP BY table
            """)
            tables_info = [
                {
                    'name': row[0],
                    'size': row[1],
                    'total_rows': row[2],
                    'last_modified': row[3]
                }
                for row in cursor.fetchall()
            ]
            
            # 获取总表数
            cursor.execute("SELECT count() FROM system.tables")
            total_tables = cursor.fetchone()[0]

            return {
                'status': 'healthy',
                'connection': True,
                'version': version,
                'total_tables': total_tables,
                'database_size': db_size,
                'uptime_seconds': uptime,
                'tables_info': tables_info,
                'stock_tables': [t for t in tables_info if t['name'].startswith('stock_')]
            }
        except Exception as e:
            logger.error(f"ClickHouse健康检查失败: {str(e)}")
            return {
                'status': 'unhealthy',
                'connection': False,
                'error': str(e)
            }
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
