# coding=utf-8
"""爬虫定时任务调度器

提供基于 APScheduler 的定时任务调度功能
"""

from datetime import datetime
from typing import Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.job import Job

from src.app import TrendRadarApp
from src.utils.time import get_beijing_time


class CrawlerScheduler:
    """爬虫定时任务调度器

    功能:
    - 基于配置自动启动定时爬取任务
    - 支持 interval(间隔) 和 cron(定时) 两种调度模式
    - 提供任务的启动、停止、暂停、恢复控制
    - 记录任务执行历史和状态
    """

    def __init__(self, config: Dict[str, Any], config_path: str = "config/config.yaml"):
        """初始化调度器

        Args:
            config: 配置字典
            config_path: 配置文件路径
        """
        self.config = config
        self.config_path = config_path
        self.scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

        # 任务执行历史
        self.execution_history: list = []
        self.max_history_size = 50

        # 当前任务状态
        self.current_job: Optional[Job] = None
        self.is_running = False

    async def start(self) -> None:
        """启动调度器"""
        scheduler_config = self.config.get("scheduler", {})

        if not scheduler_config.get("enabled", False):
            print("⚠️  定时任务调度器未启用")
            return

        # 添加爬虫任务
        self._add_crawler_job(scheduler_config)

        # 启动调度器
        self.scheduler.start()
        self.is_running = True

        print("✓ 定时任务调度器已启动")

    async def stop(self) -> None:
        """停止调度器"""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            print("✓ 定时任务调度器已停止")

    def _add_crawler_job(self, scheduler_config: Dict) -> None:
        """添加爬虫任务

        Args:
            scheduler_config: 调度器配置
        """
        trigger_type = scheduler_config.get("trigger_type", "interval")
        mode = scheduler_config.get("mode", "daily")

        if trigger_type == "interval":
            # 间隔触发模式
            interval_seconds = scheduler_config.get("interval_seconds", 3600)
            trigger = IntervalTrigger(seconds=interval_seconds, timezone="Asia/Shanghai")
            print(f"✓ 配置间隔触发: 每 {interval_seconds} 秒执行一次 ({mode} 模式)")

        elif trigger_type == "cron":
            # Cron 表达式触发模式
            cron_expr = scheduler_config.get("cron_expression", "0 * * * *")
            trigger = CronTrigger.from_crontab(cron_expr, timezone="Asia/Shanghai")
            print(f"✓ 配置 Cron 触发: {cron_expr} ({mode} 模式)")

        else:
            raise ValueError(f"不支持的触发器类型: {trigger_type}")

        # 添加任务
        self.current_job = self.scheduler.add_job(
            func=self._run_crawler_task,
            trigger=trigger,
            args=[mode],
            id="crawler_task",
            name=f"TrendRadar 爬虫任务 ({mode})",
            max_instances=1,  # 同时只运行一个实例
            coalesce=True,    # 错过的任务合并执行
            misfire_grace_time=300  # 错过任务的宽限时间(5分钟)
        )

    async def _run_crawler_task(self, mode: str) -> None:
        """执行爬虫任务

        Args:
            mode: 运行模式 (daily/current/incremental)
        """
        start_time = get_beijing_time()
        task_id = start_time.strftime("%Y%m%d_%H%M%S")

        print("\n" + "=" * 60)
        print(f"定时任务开始执行 - ID: {task_id}")
        print(f"模式: {mode} | 时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        try:
            # 创建 TrendRadarApp 实例并运行
            app = TrendRadarApp(config_path=self.config_path)
            success = app.run(mode=mode)

            end_time = get_beijing_time()
            duration = (end_time - start_time).total_seconds()

            # 记录执行历史
            self._record_execution(
                task_id=task_id,
                mode=mode,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=success
            )

            print("\n" + "=" * 60)
            print(f"定时任务执行{'成功' if success else '失败'} - 耗时: {duration:.2f} 秒")
            print("=" * 60)

        except Exception as e:
            end_time = get_beijing_time()
            duration = (end_time - start_time).total_seconds()

            # 记录失败
            self._record_execution(
                task_id=task_id,
                mode=mode,
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                success=False,
                error=str(e)
            )

            print("\n" + "=" * 60)
            print(f"定时任务执行异常: {e}")
            print("=" * 60)

            import traceback
            traceback.print_exc()

    def _record_execution(
        self,
        task_id: str,
        mode: str,
        start_time: datetime,
        end_time: datetime,
        duration: float,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """记录任务执行历史

        Args:
            task_id: 任务ID
            mode: 运行模式
            start_time: 开始时间
            end_time: 结束时间
            duration: 执行时长(秒)
            success: 是否成功
            error: 错误信息
        """
        record = {
            "task_id": task_id,
            "mode": mode,
            "start_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "duration": duration,
            "success": success,
            "error": error
        }

        self.execution_history.append(record)

        # 限制历史记录数量
        if len(self.execution_history) > self.max_history_size:
            self.execution_history.pop(0)

    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态

        Returns:
            Dict: 状态信息
        """
        scheduler_config = self.config.get("scheduler", {})

        status = {
            "enabled": scheduler_config.get("enabled", False),
            "running": self.is_running,
            "scheduler_state": "running" if self.scheduler.running else "stopped",
            "trigger_type": scheduler_config.get("trigger_type", "interval"),
            "mode": scheduler_config.get("mode", "daily"),
        }

        # 添加触发器信息
        if scheduler_config.get("trigger_type") == "interval":
            status["interval_seconds"] = scheduler_config.get("interval_seconds", 3600)
        else:
            status["cron_expression"] = scheduler_config.get("cron_expression", "0 * * * *")

        # 添加下次执行时间
        if self.current_job and self.scheduler.running:
            next_run = self.current_job.next_run_time
            if next_run:
                status["next_run_time"] = next_run.strftime("%Y-%m-%d %H:%M:%S")

        # 添加执行历史统计
        if self.execution_history:
            total = len(self.execution_history)
            success = sum(1 for r in self.execution_history if r["success"])
            failed = total - success

            status["execution_stats"] = {
                "total": total,
                "success": success,
                "failed": failed,
                "last_execution": self.execution_history[-1] if self.execution_history else None
            }

        return status

    def get_execution_history(self, limit: int = 10) -> list:
        """获取任务执行历史

        Args:
            limit: 返回的最大记录数

        Returns:
            list: 执行历史记录列表
        """
        return self.execution_history[-limit:]

    async def pause_job(self) -> bool:
        """暂停任务

        Returns:
            bool: 是否成功
        """
        if self.current_job:
            self.current_job.pause()
            print("✓ 定时任务已暂停")
            return True
        return False

    async def resume_job(self) -> bool:
        """恢复任务

        Returns:
            bool: 是否成功
        """
        if self.current_job:
            self.current_job.resume()
            print("✓ 定时任务已恢复")
            return True
        return False

    async def trigger_now(self, mode: Optional[str] = None) -> None:
        """立即触发一次任务

        Args:
            mode: 运行模式,如果为 None 则使用配置的默认模式
        """
        if mode is None:
            mode = self.config.get("scheduler", {}).get("mode", "daily")

        print(f"手动触发任务 - 模式: {mode}")
        await self._run_crawler_task(mode)
