from typing import Dict, List, Any
import pandas as pd
import backtrader as bt
from datetime import datetime
from utils.redis_helper import RedisHelper
from utils.clickhouse_helper import ClickHouseClient
from .base_loader import BaseDataLoader

class DefaultDataLoader(BaseDataLoader):
    """默认数据加载器"""
    
    def _load_basic_data(self) -> None:
        """加载基础数据"""
        # 加载股票基本信息
        self.stock_info = RedisHelper.get_df('stock:basic')
        
        # 加载交易日历
        calendar_df = RedisHelper.get_df('stock:calendar')
        self.trade_calendar = calendar_df['trade_date'].tolist() if not calendar_df.empty else []
        
        # 加载最新行情数据
        self.latest_quotes = RedisHelper.get_df('stock:realtime')
    
    def _load_market_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """加载市场数据"""
        if code.startswith('0') or code.startswith('3') or code.startswith('6'):
            return self._load_stock_data(code, start_date, end_date)
        else:
            return self._load_index_data(code, start_date, end_date)
    
    def _create_data_feed(self, df: pd.DataFrame, start_date: str, end_date: str,
                         name: str = None) -> bt.feeds.PandasData:
        """创建数据源对象"""
        return bt.feeds.PandasData(
            dataname=df,
            datetime='trade_date',
            open='open',
            high='high',
            low='low',
            close='close',
            volume='volume',
            openinterest=-1,
            fromdate=pd.to_datetime(start_date),
            todate=pd.to_datetime(end_date),
            name=name,
            plot=True
        )
    
    def _load_stock_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从数据库加载股票数据"""
        query = """
        SELECT 
            trade_date,
            open,
            high,
            low,
            close,
            volume,
            amount
        FROM stock_daily 
        WHERE stock_code = %(code)s 
        AND trade_date BETWEEN %(start_date)s AND %(end_date)s
        ORDER BY trade_date
        """
        params = {'code': code, 'start_date': start_date, 'end_date': end_date}
        df = ClickHouseClient.query_df(query, params)
        
        if not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        return df
    
    def _load_index_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """从数据库加载指数数据"""
        query = """
        SELECT 
            trade_date,
            open,
            high,
            low,
            close,
            volume,
            amount
        FROM index_daily 
        WHERE index_code = %(code)s 
        AND trade_date BETWEEN %(start_date)s AND %(end_date)s
        ORDER BY trade_date
        """
        params = {'code': code, 'start_date': start_date, 'end_date': end_date}
        df = ClickHouseClient.query_df(query, params)
        
        if not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
        
        return df 