from abc import ABC, abstractmethod
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor
import threading
from utils.logger import Logger

logger = Logger.get_logger(__name__)

class OutputObserver(ABC):
    """结果输出观察者基类"""
    
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = threading.Lock()
    
    def _async_output(self, output_func, *args, **kwargs):
        """异步执行输出"""
        self._executor.submit(self._safe_output, output_func, *args, **kwargs)
    
    def _safe_output(self, output_func, *args, **kwargs):
        """线程安全的输出执行"""
        with self._lock:
            try:
                output_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"输出执行失败: {str(e)}")
    
    def on_results(self, results: Dict[str, Any]) -> None:
        """处理回测结果"""
        if not results.get('success', False):
            self._async_output(self._process_error, results.get('error', '未知错误'))
            return
        
        # 基本信息
        self._async_output(self._process_basic_info, results)
        
        # 获取观察者数据
        observer_data = results.get('observer_data', {})
        



    @abstractmethod
    def _process_basic_info(self, results: Dict[str, Any]) -> None:
        """处理基本信息"""
        pass

