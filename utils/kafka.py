from typing import Optional, Any, List, Dict, Union, Callable
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import KafkaError
import json
import yaml
from pathlib import Path
import logging
from utils.uitl import get_root_path
from queue import Queue
from threading import Lock
import pandas as pd

class KafkaClient:
    """
    Kafka 工具类
    提供常用的 Kafka 操作方法，使用连接池管理连接
    所有配置从 config/application.yaml 读取
    
    Attributes:
        _producer_pool: 生产者连接池
        _consumer_pool: 消费者连接池
        _admin_client: 管理客户端
    """
    
    _producer_pool: Queue = Queue()
    _consumer_pools: Dict[str, Queue] = {}
    _pool_lock = Lock()
    _admin_client = None
    _max_pool_size = 10

    @classmethod
    def _get_kafka_config(cls) -> Dict:
        """获取Kafka配置"""
        config_path = Path(get_root_path(), "config/application.yaml")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('kafka', {})

    @classmethod
    def _create_producer(cls) -> KafkaProducer:
        """创建生产者实例"""
        kafka_config = cls._get_kafka_config()
        return KafkaProducer(
            bootstrap_servers=f"{kafka_config.get('host', 'localhost')}:{kafka_config.get('port', 9092)}",
            value_serializer=lambda x: json.dumps(x).encode('utf-8'),
            acks='all',
            retries=3
        )

    @classmethod
    def _get_producer(cls) -> KafkaProducer:
        """从连接池获取生产者"""
        try:
            if cls._producer_pool.empty():
                if cls._producer_pool.qsize() < cls._max_pool_size:
                    return cls._create_producer()
            return cls._producer_pool.get_nowait()
        except Exception:
            return cls._create_producer()

    @classmethod
    def _return_producer(cls, producer: KafkaProducer):
        """归还生产者到连接池"""
        if cls._producer_pool.qsize() < cls._max_pool_size:
            cls._producer_pool.put(producer)
        else:
            producer.close()

    @classmethod
    def _get_consumer(cls, topic: str, group_id: str = None, **kwargs) -> KafkaConsumer:
        """获取或创建消费者"""
        key = f"{topic}:{group_id}"
        with cls._pool_lock:
            if key not in cls._consumer_pools:
                cls._consumer_pools[key] = Queue()

        pool = cls._consumer_pools[key]
        try:
            if not pool.empty():
                return pool.get_nowait()
        except Exception:
            pass

        kafka_config = cls._get_kafka_config()
        return KafkaConsumer(
            topic,
            bootstrap_servers=f"{kafka_config.get('host', 'localhost')}:{kafka_config.get('port', 9092)}",
            group_id=group_id,
            value_deserializer=lambda x: json.loads(x.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            **kwargs
        )

    @classmethod
    def _return_consumer(cls, consumer: KafkaConsumer, topic: str, group_id: str = None):
        """归还消费者到连接池"""
        key = f"{topic}:{group_id}"
        pool = cls._consumer_pools.get(key)
        if pool and pool.qsize() < cls._max_pool_size:
            pool.put(consumer)
        else:
            consumer.close()

    @staticmethod
    def send_message(topic: str, message: Any, key: bytes = None) -> bool:
        """
        发送消息到指定主题
        
        Args:
            topic: 主题名称
            message: 消息内容（会自动序列化为JSON）
            key: 消息键（可选）
            
        Returns:
            bool: 发送是否成功
            
        Examples:
            >>> KafkaClient.send_message('test_topic', {'data': 'test'})
            True
        """
        producer = None
        try:
            producer = KafkaClient._get_producer()
            future = producer.send(topic, value=message, key=key)
            future.get(timeout=10)  # 等待发送完成
            return True
        except Exception as e:
            logging.error(f"Failed to send message to topic {topic}: {str(e)}")
            return False
        finally:
            if producer:
                KafkaClient._return_producer(producer)

    @staticmethod
    def send_df(topic: str, df: pd.DataFrame, batch_size: int = 100) -> bool:
        """
        发送DataFrame数据到指定主题
        
        Args:
            topic: 主题名称
            df: 要发送的DataFrame
            batch_size: 批量发送的大小
            
        Returns:
            bool: 发送是否成功
        """
        producer = None
        try:
            producer = KafkaClient._get_producer()
            records = df.to_dict('records')
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                futures = []
                for record in batch:
                    future = producer.send(topic, value=record)
                    futures.append(future)
                
                # 等待批次发送完成
                for future in futures:
                    future.get(timeout=10)
                
            return True
        except Exception as e:
            logging.error(f"Failed to send DataFrame to topic {topic}: {str(e)}")
            return False
        finally:
            if producer:
                KafkaClient._return_producer(producer)

    @staticmethod
    def consume_messages(topic: str, 
                        handler: Callable[[Dict], None],
                        group_id: str = None,
                        timeout_ms: int = 1000,
                        max_messages: int = None) -> None:
        """
        消费主题消息
        
        Args:
            topic: 主题名称
            handler: 消息处理函数
            group_id: 消费者组ID
            timeout_ms: 轮询超时时间（毫秒）
            max_messages: 最大消费消息数（None表示持续消费）
            
        Examples:
            >>> def print_message(msg):
            ...     print(f"Received: {msg}")
            >>> KafkaClient.consume_messages('test_topic', print_message)
        """
        consumer = None
        try:
            consumer = KafkaClient._get_consumer(topic, group_id)
            message_count = 0
            
            while True:
                messages = consumer.poll(timeout_ms=timeout_ms)
                for topic_partition, partition_messages in messages.items():
                    for message in partition_messages:
                        handler(message.value)
                        message_count += 1
                        
                        if max_messages and message_count >= max_messages:
                            return
                            
        except Exception as e:
            logging.error(f"Error consuming messages from topic {topic}: {str(e)}")
        finally:
            if consumer:
                KafkaClient._return_consumer(consumer, topic, group_id)

    @staticmethod
    def create_topic(topic: str, num_partitions: int = 1, replication_factor: int = 1) -> bool:
        """
        创建新主题
        
        Args:
            topic: 主题名称
            num_partitions: 分区数
            replication_factor: 副本因子
            
        Returns:
            bool: 创建是否成功
        """
        try:
            if not KafkaClient._admin_client:
                kafka_config = KafkaClient._get_kafka_config()
                KafkaClient._admin_client = KafkaAdminClient(
                    bootstrap_servers=f"{kafka_config.get('host', 'localhost')}:{kafka_config.get('port', 9092)}"
                )
            
            topic_list = [
                NewTopic(
                    name=topic,
                    num_partitions=num_partitions,
                    replication_factor=replication_factor
                )
            ]
            KafkaClient._admin_client.create_topics(topic_list)
            return True
        except Exception as e:
            logging.error(f"Failed to create topic {topic}: {str(e)}")
            return False

    @staticmethod
    def delete_topic(topic: str) -> bool:
        """
        删除主题
        
        Args:
            topic: 主题名称
            
        Returns:
            bool: 删除是否成功
        """
        try:
            if not KafkaClient._admin_client:
                kafka_config = KafkaClient._get_kafka_config()
                KafkaClient._admin_client = KafkaAdminClient(
                    bootstrap_servers=f"{kafka_config.get('host', 'localhost')}:{kafka_config.get('port', 9092)}"
                )
            
            KafkaClient._admin_client.delete_topics([topic])
            return True
        except Exception as e:
            logging.error(f"Failed to delete topic {topic}: {str(e)}")
            return False

    @staticmethod
    def close_all():
        """
        关闭所有连接池中的连接
        在程序结束时调用
        """
        # 关闭生产者连接池
        while not KafkaClient._producer_pool.empty():
            producer = KafkaClient._producer_pool.get()
            producer.close()

        # 关闭消费者连接池
        for pool in KafkaClient._consumer_pools.values():
            while not pool.empty():
                consumer = pool.get()
                consumer.close()

        # 关闭管理客户端
        if KafkaClient._admin_client:
            KafkaClient._admin_client.close()
            KafkaClient._admin_client = None

        logging.info("All Kafka connections closed")
