from typing import Dict, Any
import backtrader as bt
from utils.logger import Logger
from .registry import AnalyzerRegistry

logger = Logger.get_logger(__name__)

class AnalyzerChainBuilder:
    """分析器链构建器"""
    
    @classmethod
    def add_analyzers(cls, cerebro: bt.Cerebro) -> None:
        """添加分析器到回测引擎"""
        enabled_analyzers = AnalyzerRegistry.get_enabled_analyzers()
        
        for name, info in enabled_analyzers.items():
            try:
                analyzer_class = info['class']
                cerebro.addanalyzer(analyzer_class, _name=name)
                logger.debug(f"添加分析器: {name}")
            except Exception as e:
                logger.error(f"添加分析器 {name} 失败: {str(e)}")
    
    @classmethod
    def setup_analyzers(cls, analyzers: Dict[str, bool] = None) -> Dict[str, bool]:
        """配置分析器"""
        if analyzers is None:
            analyzers = {
                name: True for name in AnalyzerRegistry._analyzers.keys()
            }
        
        # 更新分析器状态
        for name, enabled in analyzers.items():
            if enabled:
                AnalyzerRegistry.enable(name)
            else:
                AnalyzerRegistry.disable(name)
        
        return analyzers
    
    @classmethod
    def get_analysis_results(cls, strategy: bt.Strategy, analyzers) -> Dict[str, Any]:
        """获取分析结果"""
        try:
            results = {}
            
            # 处理 ItemCollection 类型的分析器集合
            if hasattr(analyzers, '_items'):  # backtrader 的 ItemCollection
                items = analyzers._items
            elif hasattr(analyzers, '__iter__'):  # 可迭代对象
                items = analyzers
            else:
                items = []
            
            # 遍历分析器
            for analyzer in items:
                try:
                    # 获取分析器名称
                    name = analyzer.__class__.__name__.lower()
                    if hasattr(analyzer, '_name'):
                        name = analyzer._name
                    
                    # 获取分析结果
                    analysis = analyzer.get_analysis()
                    
                    # 处理不同类型的结果
                    if isinstance(analysis, dict):
                        results[name] = analysis
                    elif hasattr(analysis, '_asdict'):  # namedtuple
                        results[name] = analysis._asdict()
                    elif hasattr(analysis, '__dict__'):  # 对象
                        results[name] = analysis.__dict__
                    else:
                        # 其他类型直接存储
                        results[name] = analysis
                        
                    logger.debug(f"成功获取分析器 {name} 的结果")
                    
                except Exception as e:
                    logger.error(f"获取分析器结果失败: {str(e)}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"获取分析结果失败: {str(e)}")
            return {} 