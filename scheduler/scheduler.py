from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from typing import Callable, Dict, Any, Union
from utils.logger import Logger
import uuid

class TaskScheduler:
    """定时任务调度器
    
    用法示例:    ```python
    scheduler = TaskScheduler()
    
    # 添加定时任务
    scheduler.add_job(
        func=your_function,
        trigger="0 9 * * 1-5",  # 工作日上午9点执行
        name="market_data_update",
        kwargs={"param1": "value1"}
    )
    
    # 启动调度器
    scheduler.start()    ```
    """
    
    def __init__(self):
        self.logger = Logger.get_logger(__name__)
        self.scheduler = BackgroundScheduler()
        self.jobs = {}
    
    def add_job(self, func: Callable, trigger: Union[str, int], name: str = None, 
                kwargs: Dict[str, Any] = None, job_id: str = None) -> str:
        """添加定时任务
        
        Args:
            func: 要执行的函数
            trigger: cron表达式或间隔秒数 (例如: "0 9 * * 1-5" 或 2)
            name: 任务名称，用于生成可读的任务ID
            kwargs: 传递给函数的参数字典
            job_id: 任务ID，如果不指定则根据name和func自动生成
        
        Returns:
            str: 任务ID
        """
        try:
            # 生成任务ID
            if not job_id:
                base_name = name or func.__name__
                suffix = str(uuid.uuid4())[:8]
                job_id = f"{base_name}_{suffix}"
            
            if job_id in self.jobs:
                raise ValueError(f"Job ID '{job_id}' already exists")
            
            # 根据trigger类型选择触发器
            if isinstance(trigger, str):
                job_trigger = CronTrigger.from_crontab(trigger)
                schedule_desc = f"cron: {trigger}"
            else:
                job_trigger = IntervalTrigger(seconds=trigger)
                schedule_desc = f"interval: {trigger}s"
            
            job = self.scheduler.add_job(
                func=func,
                trigger=job_trigger,
                id=job_id,
                kwargs=kwargs or {},
                misfire_grace_time=None
            )
            
            self.jobs[job.id] = {
                'name': name or func.__name__,
                'func': func.__name__,
                'trigger': schedule_desc,
                'kwargs': kwargs
            }
            
            self.logger.info(f"添加定时任务成功: [{name or func.__name__}] {job.id}, 执行计划: {schedule_desc}")
            return job.id
            
        except Exception as e:
            self.logger.error(f"添加定时任务失败: {str(e)}")
            raise
    
    def remove_job(self, job_id: str) -> bool:
        """移除定时任务
        
        Args:
            job_id: 任务ID
            
        Returns:
            bool: 是否成功移除
        """
        try:
            self.scheduler.remove_job(job_id)
            self.jobs.pop(job_id, None)
            self.logger.info(f"移除定时任务成功: {job_id}")
            return True
        except Exception as e:
            self.logger.error(f"移除定时任务失败: {str(e)}")
            return False
    
    def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            self.logger.info("调度器启动成功")
        except Exception as e:
            self.logger.error(f"调度器启动失败: {str(e)}")
            raise
    
    def shutdown(self):
        """关闭调度器"""
        try:
            self.scheduler.shutdown()
            self.logger.info("调度器已关闭")
        except Exception as e:
            self.logger.error(f"调度器关闭失败: {str(e)}")
            raise
    
    def get_jobs(self) -> Dict[str, Dict]:
        """获取所有任务信息"""
        return self.jobs.copy() 