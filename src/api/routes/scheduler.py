# coding=utf-8
"""定时任务控制路由"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/scheduler", tags=["定时任务控制"])

# 全局调度器实例（由 server.py 注入）
_scheduler = None


def set_scheduler(scheduler):
    """设置调度器实例（依赖注入）"""
    global _scheduler
    _scheduler = scheduler


def get_scheduler():
    """获取调度器实例"""
    if _scheduler is None:
        raise HTTPException(status_code=503, detail="调度器未初始化")
    return _scheduler


class TriggerRequest(BaseModel):
    """手动触发请求"""
    mode: Optional[str] = None


@router.get("/status", summary="获取调度器状态")
async def get_scheduler_status():
    """获取定时任务调度器的当前状态

    返回:
    - enabled: 是否启用
    - running: 是否运行中
    - trigger_type: 触发器类型 (interval/cron)
    - mode: 运行模式
    - next_run_time: 下次执行时间
    - execution_stats: 执行统计信息
    """
    scheduler = get_scheduler()
    status = scheduler.get_status()
    return {
        "success": True,
        "data": status
    }


@router.get("/history", summary="获取执行历史")
async def get_execution_history(
    limit: int = Query(10, ge=1, le=50, description="返回的最大记录数")
):
    """获取任务执行历史记录

    参数:
    - limit: 返回的最大记录数 (1-50)

    返回:
    - 执行历史记录列表,包含任务ID、模式、开始/结束时间、执行时长、是否成功等信息
    """
    scheduler = get_scheduler()
    history = scheduler.get_execution_history(limit=limit)
    return {
        "success": True,
        "data": {
            "total": len(history),
            "records": history
        }
    }


@router.post("/pause", summary="暂停任务")
async def pause_job():
    """暂停定时任务（不会停止调度器,只是暂停任务执行）

    返回:
    - success: 是否成功
    """
    scheduler = get_scheduler()
    success = await scheduler.pause_job()

    if not success:
        raise HTTPException(status_code=400, detail="任务暂停失败,可能任务不存在")

    return {
        "success": True,
        "message": "任务已暂停"
    }


@router.post("/resume", summary="恢复任务")
async def resume_job():
    """恢复已暂停的任务

    返回:
    - success: 是否成功
    """
    scheduler = get_scheduler()
    success = await scheduler.resume_job()

    if not success:
        raise HTTPException(status_code=400, detail="任务恢复失败,可能任务不存在")

    return {
        "success": True,
        "message": "任务已恢复"
    }


@router.post("/trigger", summary="立即触发任务")
async def trigger_now(request: TriggerRequest):
    """立即手动触发一次爬取任务（不影响定时计划）

    参数:
    - mode: 运行模式 (daily/current/incremental),为空则使用配置的默认模式

    返回:
    - success: 是否成功触发
    """
    scheduler = get_scheduler()

    # 异步触发任务（不等待执行完成）
    import asyncio
    asyncio.create_task(scheduler.trigger_now(mode=request.mode))

    return {
        "success": True,
        "message": f"任务已触发 (模式: {request.mode or '默认'}),正在后台执行"
    }
