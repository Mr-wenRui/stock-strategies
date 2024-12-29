import pandas as pd
import json
from datetime import datetime, timedelta
from utils.redis import RedisClient
from utils.clickhouse import ClickHouseClient
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class DataLoader:
    """数据加载器，用于加载回测所需的各类数据"""
    
    def __init__(self):
        self.redis_client = RedisClient()
        self.ch_client = ClickHouseClient()
        
        # 检查数据源健康状态
        self._check_data_sources()

    def _check_data_sources(self):
        """检查数据源是否正常"""
        # 检查Redis连接
        redis_health = self.redis_client.health_check()
        if redis_health['status'] != 'healthy':
            logger.error(f"Redis连接异常: {redis_health.get('error', 'Unknown error')}")
            
        # 检查ClickHouse连接
        ch_health = self.ch_client.health_check()
        if ch_health['status'] != 'healthy':
            logger.error(f"ClickHouse连接异常: {ch_health.get('error', 'Unknown error')}")

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        try:
            df = self.redis_client.get_df('stock:list')
            if df is None or df.empty:
                logger.warning("Redis中未找到股票列表数据")
                return pd.DataFrame()
            return df
        except Exception as e:
            logger.error(f"获取股票列表失败: {str(e)}")
            return pd.DataFrame()

    def get_stock_basic(self, stock_code: str = None) -> pd.DataFrame:
        """获取股票基础信息"""
        try:
            df = self.redis_client.get_df('stock:basic')
            if df is None or df.empty:
                logger.warning("Redis中未找到股票基础信息")
                return pd.DataFrame()
            
            # 确保列名正确
            expected_columns = ['stock_code', 'stock_name', 'list_date', 'updated_at']
            if not all(col in df.columns for col in expected_columns):
                logger.error("股票基础信息数据结构不符合预期")
                return pd.DataFrame()
            
            if stock_code:
                return df[df['stock_code'] == stock_code]
            return df
        except Exception as e:
            logger.error(f"获取股票基础信息失败: {str(e)}")
            return pd.DataFrame()

    def get_trade_calendar(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """获取交易日历"""
        try:
            df = self.redis_client.get_df('stock:calendar')
            if df is None or df.empty:
                logger.warning("Redis中未找到交易日历数据")
                return pd.DataFrame()
            
            if start_date and end_date:
                return df[(df['trade_date'] >= start_date) & (df['trade_date'] <= end_date)]
            return df
        except Exception as e:
            logger.error(f"获取交易日历失败: {str(e)}")
            return pd.DataFrame()

    def get_history_data(self, stock_codes: list, start_date: str, end_date: str) -> pd.DataFrame:
        """获取历史数据"""
        try:
            if isinstance(stock_codes, str):
                stock_codes = [stock_codes]
                
            placeholders = ', '.join([f"'{code}'" for code in stock_codes])
            query = f"""
                SELECT 
                    trade_date,
                    stock_code as code,
                    stock_name,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    amount,
                    turnover_rate,
                    pct_change
                FROM stock_daily
                WHERE stock_code IN ({placeholders})
                    AND trade_date BETWEEN '{start_date}' AND '{end_date}'
                ORDER BY trade_date
            """
            
            df = self.ch_client.query_df(query)
            if df.empty:
                logger.warning(f"未找到股票历史数据: {stock_codes}")
                return pd.DataFrame()
                
            # 计算市值（这里用收盘价 * 成交量/换手率 来估算）
            df['market_cap'] = df.apply(
                lambda x: x['close'] * (x['volume'] / (x['turnover_rate'] / 100)) 
                if x['turnover_rate'] > 0 else 0, 
                axis=1
            )
            
            return df
            
        except Exception as e:
            logger.error(f"获取历史数据失败: {str(e)}")
            return pd.DataFrame()

    def filter_stocks(self, min_listing_days: int = 250, exclude_st: bool = True) -> list:
        """筛选符合条件的股票"""
        try:
            stock_list_df = self.get_stock_list()
            basic_info_df = self.get_stock_basic()
            current_date = datetime.now().strftime('%Y%m%d')
            
            if stock_list_df.empty or basic_info_df.empty:
                logger.warning("无法获取股票列表或基础信息")
                return []
            
            # 合并股票列表和基础信息
            df = pd.merge(stock_list_df, basic_info_df, on='stock_code', how='inner')
            
            # 计算上市天数
            df['listing_days'] = df['list_date'].apply(
                lambda x: (datetime.strptime(current_date, '%Y%m%d') - 
                          datetime.strptime(str(x), '%Y%m%d')).days 
                if pd.notna(x) else 0
            )
            
            # 应用上市天数过滤条件
            mask = df['listing_days'] >= min_listing_days
            
            # 通过股票名称判断是否为ST股票
            if exclude_st:
                # 检查股票名称中是否包含'ST'（不区分大小写）
                df['is_st'] = df['stock_name'].str.contains('ST', case=False)
                mask &= ~df['is_st']
                
                # 记录ST股票数量
                st_count = df['is_st'].sum()
                logger.info(f"发现 {st_count} 只ST股票")
            
            filtered_df = df[mask]
            filtered_stocks = filtered_df['stock_code'].tolist()
            
            logger.info(f"筛选出 {len(filtered_stocks)} 只符合条件的股票")
            
            # 记录详细的过滤信息
            total_stocks = len(df)
            excluded_listing_days = len(df[df['listing_days'] < min_listing_days])
            excluded_st = len(df[df['is_st']]) if exclude_st else 0
            
            logger.info(f"""股票筛选详情:
                总股票数: {total_stocks}
                上市时间不足: {excluded_listing_days}
                ST股票数: {excluded_st if exclude_st else '不过滤'}
                最终保留: {len(filtered_stocks)}
            """)
            
            return filtered_stocks
            
        except Exception as e:
            logger.error(f"筛选股票失败: {str(e)}")
            return []

    def get_latest_trading_date(self) -> str:
        """获取最新交易日期"""
        try:
            calendar_df = self.get_trade_calendar()
            if calendar_df.empty:
                return None
            return calendar_df['trade_date'].max()
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {str(e)}")
            return None

    def get_previous_trading_date(self, date_str: str, n: int = 1) -> str:
        """获取前n个交易日日期"""
        try:
            calendar_df = self.get_trade_calendar()
            if calendar_df.empty:
                return None
                
            # 按日期排序
            calendar_df = calendar_df.sort_values('trade_date')
            dates = calendar_df['trade_date'].tolist()
            
            try:
                current_idx = dates.index(date_str)
                if current_idx >= n:
                    return dates[current_idx - n]
            except ValueError:
                logger.warning(f"日期 {date_str} 不在交易日历中")
            return None
        except Exception as e:
            logger.error(f"获取前一交易日失败: {str(e)}")
            return None

    def check_data_availability(self, stock_code: str) -> bool:
        """检查股票数据是否可用"""
        try:
            latest_date = self.get_latest_trading_date()
            if not latest_date:
                logger.warning("无法获取最新交易日期")
                return False
                
            realtime_data = self.get_realtime_data(stock_code)
            if not realtime_data:
                logger.warning(f"股票 {stock_code} 无实时数据")
                return False
                
            basic_info = self.get_stock_basic(stock_code)
            if not basic_info:
                logger.warning(f"股票 {stock_code} 无基础信息")
                return False
                
            return True
        except Exception as e:
            logger.error(f"检查股票 {stock_code} 数据可用性失败: {str(e)}")
            return False

    def get_realtime_data(self, stock_code: str = None) -> pd.DataFrame:
        """获取实时行情数据"""
        try:
            df = self.redis_client.get_df('stock:realtime')
            if df is None or df.empty:
                logger.warning("Redis中未找到实时行情数据")
                return pd.DataFrame()
            if stock_code:
                return df[df['stock_code'] == stock_code]
            return df
        except Exception as e:
            logger.error(f"获取实时行情数据失败: {str(e)}")
            return pd.DataFrame() 