from typing import Dict, Optional
import backtrader as bt
from .registry import ObserverRegistry

class ObserverBuilder:
    """观察者构建器"""
    
    @classmethod
    def setup_observers(cls, cerebro: bt.Cerebro, config: Optional[Dict[str, bool]] = None) -> Dict[str, bool]:
        """设置观察者"""
        # 添加内置观察者
        cls._add_builtin_observers(cerebro)
        # 如果提供了配置，更新观察者状态
        if config is not None:
            for name, enabled in config.items():
                if enabled:
                    ObserverRegistry.enable(name)
                else:
                    ObserverRegistry.disable(name)
        
        # 添加启用的观察者
        for name, observer_class in ObserverRegistry.get_enabled_observers().items():
            cerebro.addobserver(observer_class)
        
        # 返回当前配置
        return {name: ObserverRegistry.is_enabled(name) 
                for name in ObserverRegistry._observers} 
    
    
    # 添加内置观察者
    @classmethod
    def _add_builtin_observers(cls, cerebro: bt.Cerebro) -> None:
        """添加内置观察者"""
        cerebro.addobserver(bt.observers.Broker)
        cerebro.addobserver(bt.observers.Trades)
        cerebro.addobserver(bt.observers.BuySell)
        cerebro.addobserver(bt.observers.Value)
        cerebro.addobserver(bt.observers.DrawDown)
        cerebro.addobserver(bt.observers.TimeReturn)
        cerebro.addobserver(bt.observers.Benchmark)


