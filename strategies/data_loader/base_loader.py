from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union
import pandas as pd
import backtrader as bt
from datetime import datetime
from utils.redis_helper import RedisHelper
from utils.clickhouse_helper import ClickHouseClient
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class BaseDataLoader(ABC):
    """数据加载器基类"""
    
    def __init__(self):
        self.data_load_time = None
        self.stock_info = None
        self.trade_calendar = None
        self.latest_quotes = None
    
    def load_data(self, debug: bool = False) -> None:
        """加载基础数据"""
        try:
            # 加载基础数据
            self._load_basic_data()
            
            # 记录加载时间
            self.data_load_time = datetime.now()
            
            # 调试模式下打印信息
            if debug:
                self._log_data_info()
                
        except Exception as e:
            logger.error(f"加载数据失败: {str(e)}")
            raise
    
    def create_data_feeds(self, codes: Union[str, List[str]], 
                         start_date: str, end_date: str,
                         cerebro: bt.Cerebro) -> None:
        """创建数据源并添加到cerebro"""
        if isinstance(codes, str):
            codes = [codes]
            
        for code in codes:
            try:
                # 加载数据
                df = self._load_market_data(code, start_date, end_date)
                if df.empty:
                    logger.warning(f"未找到股票 {code} 的数据")
                    continue
                
                # 创建数据源
                data_feed = self._create_data_feed(df, start_date, end_date, code)
                
                # 添加到cerebro
                cerebro.adddata(data_feed)
                logger.debug(f"成功添加 {code} 的数据")
                
            except Exception as e:
                logger.error(f"处理 {code} 的数据失败: {str(e)}")
    
    @abstractmethod
    def _load_basic_data(self) -> None:
        """加载基础数据（由子类实现）"""
        pass
    
    @abstractmethod
    def _load_market_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """加载市场数据（由子类实现）"""
        pass
    
    @abstractmethod
    def _create_data_feed(self, df: pd.DataFrame, start_date: str, end_date: str,
                         name: str = None) -> bt.feeds.PandasData:
        """创建数据源对象（由子类实现）"""
        pass
    
    def _log_data_info(self) -> None:
        """打印数据加载信息"""
        logger.info("策略数据加载完成")
        if self.trade_calendar is not None:
            logger.info(f"加载了 {len(self.trade_calendar)} 个交易日")
        if self.stock_info is not None:
            logger.info(f"加载了 {len(self.stock_info)} 只股票的基本信息")
        if self.latest_quotes is not None:
            logger.info(f"加载了 {len(self.latest_quotes)} 只股票的实时行情") 