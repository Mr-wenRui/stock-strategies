from typing import Optional, Any, List, Tuple
import backtrader as bt
from datetime import datetime
from utils.logger import Logger

logger = Logger.get_logger(__name__)

def get_data_series(data: bt.AbstractDataBase) -> Tuple[List[str], List[Any]]:
    """
    安全地获取数据序列
    
    参数:
        data: Backtrader数据对象
        
    返回:
        (dates, values): 日期列表和数据列表
    """
    dates = []
    values = []
    
    # 获取数据缓冲区的长度
    size = len(data.lines.datetime.array)
    
    # 遍历数据缓冲区
    for i in range(size):
        try:
            # 获取日期时间戳
            dt_stamp = data.lines.datetime.array[i]
            if dt_stamp == 0:  # 跳过无效数据
                continue
                
            # 转换为日期
            dt = bt.num2date(dt_stamp)
            dates.append(dt.strftime('%Y-%m-%d'))
            
            # 获取数据值
            values.append(data.lines.close.array[i])
        except Exception as e:
            logger.error(f"获取数据时发生错误: {str(e)}")
            continue
            
    return dates, values

def get_position_series(strategy: bt.Strategy) -> Tuple[List[str], List[float]]:
    """
    获取持仓数据序列
    
    参数:
        strategy: 策略对象
        
    返回:
        (dates, positions): 日期列表和持仓列表
    """
    data = strategy.data0  # 使用第一个数据源
    dates = []
    positions = []
    
    # 获取数据缓冲区的长度
    size = len(data.lines.datetime.array)
    
    # 遍历数据缓冲区
    for i in range(size):
        try:
            # 获取日期时间戳
            dt_stamp = data.lines.datetime.array[i]
            if dt_stamp == 0:  # 跳过无效数据
                continue
                
            # 转换为日期
            dt = bt.num2date(dt_stamp)
            dates.append(dt.strftime('%Y-%m-%d'))
            
            # 获取持仓
            pos = strategy.getposition(data).size
            positions.append(pos)
        except Exception as e:
            logger.error(f"获取持仓数据时发生错误: {str(e)}")
            continue
            
    return dates, positions 