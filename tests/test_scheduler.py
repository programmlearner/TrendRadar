# coding=utf-8
"""测试定时任务调度器功能"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.api.scheduler.task_scheduler import CrawlerScheduler


@pytest.fixture
def mock_config():
    """模拟配置"""
    return {
        "SCHEDULER_CONFIG": {
            "ENABLED": True,
            "TRIGGER_TYPE": "interval",
            "MODE": "daily",
            "INTERVAL_SECONDS": 5,  # 测试用短间隔
            "CRON_EXPRESSION": "0 * * * *"
        }
    }


@pytest.fixture
def scheduler(mock_config):
    """创建调度器实例"""
    return CrawlerScheduler(config=mock_config, config_path="config/config.yaml")


@pytest.mark.asyncio
async def test_scheduler_initialization(scheduler):
    """测试调度器初始化"""
    assert scheduler is not None
    assert scheduler.is_running is False
    assert scheduler.execution_history == []


@pytest.mark.asyncio
async def test_scheduler_disabled_config():
    """测试禁用调度器配置"""
    config = {
        "SCHEDULER_CONFIG": {
            "ENABLED": False
        }
    }
    scheduler = CrawlerScheduler(config=config, config_path="config/config.yaml")
    await scheduler.start()

    assert scheduler.is_running is False
    assert scheduler.current_job is None


@pytest.mark.asyncio
async def test_scheduler_interval_trigger(mock_config):
    """测试间隔触发器配置"""
    scheduler = CrawlerScheduler(config=mock_config, config_path="config/config.yaml")

    # 模拟 TrendRadarApp
    with patch('src.api.scheduler.task_scheduler.TrendRadarApp') as MockApp:
        mock_app = Mock()
        mock_app.run.return_value = True
        MockApp.return_value = mock_app

        await scheduler.start()

        assert scheduler.is_running is True
        assert scheduler.current_job is not None
        assert scheduler.current_job.id == "crawler_task"

        # 清理
        await scheduler.stop()


@pytest.mark.asyncio
async def test_scheduler_cron_trigger():
    """测试 Cron 触发器配置"""
    config = {
        "SCHEDULER_CONFIG": {
            "ENABLED": True,
            "TRIGGER_TYPE": "cron",
            "MODE": "current",
            "CRON_EXPRESSION": "0 * * * *"
        }
    }
    scheduler = CrawlerScheduler(config=config, config_path="config/config.yaml")

    with patch('src.api.scheduler.task_scheduler.TrendRadarApp') as MockApp:
        mock_app = Mock()
        mock_app.run.return_value = True
        MockApp.return_value = mock_app

        await scheduler.start()

        assert scheduler.is_running is True
        assert scheduler.current_job is not None

        # 清理
        await scheduler.stop()


@pytest.mark.asyncio
async def test_run_crawler_task_success(scheduler):
    """测试爬虫任务执行成功"""
    with patch('src.api.scheduler.task_scheduler.TrendRadarApp') as MockApp:
        mock_app = Mock()
        mock_app.run.return_value = True
        MockApp.return_value = mock_app

        await scheduler._run_crawler_task(mode="daily")

        # 检查执行历史记录
        assert len(scheduler.execution_history) == 1
        record = scheduler.execution_history[0]
        assert record["mode"] == "daily"
        assert record["success"] is True
        assert record["error"] is None
        assert "task_id" in record
        assert "duration" in record


@pytest.mark.asyncio
async def test_run_crawler_task_failure(scheduler):
    """测试爬虫任务执行失败"""
    with patch('src.api.scheduler.task_scheduler.TrendRadarApp') as MockApp:
        MockApp.side_effect = Exception("测试异常")

        await scheduler._run_crawler_task(mode="incremental")

        # 检查执行历史记录
        assert len(scheduler.execution_history) == 1
        record = scheduler.execution_history[0]
        assert record["mode"] == "incremental"
        assert record["success"] is False
        assert "测试异常" in record["error"]


@pytest.mark.asyncio
async def test_get_status(mock_config):
    """测试获取状态"""
    scheduler = CrawlerScheduler(config=mock_config, config_path="config/config.yaml")

    with patch('src.api.scheduler.task_scheduler.TrendRadarApp'):
        await scheduler.start()

        status = scheduler.get_status()

        assert status["enabled"] is True
        assert status["running"] is True
        assert status["trigger_type"] == "interval"
        assert status["mode"] == "daily"
        assert status["interval_seconds"] == 5

        await scheduler.stop()


@pytest.mark.asyncio
async def test_get_execution_history(scheduler):
    """测试获取执行历史"""
    # 手动添加一些历史记录
    for i in range(5):
        scheduler.execution_history.append({
            "task_id": f"test_{i}",
            "mode": "daily",
            "success": True
        })

    history = scheduler.get_execution_history(limit=3)
    assert len(history) == 3
    assert history[0]["task_id"] == "test_2"
    assert history[-1]["task_id"] == "test_4"


@pytest.mark.asyncio
async def test_pause_and_resume_job(mock_config):
    """测试暂停和恢复任务"""
    scheduler = CrawlerScheduler(config=mock_config, config_path="config/config.yaml")

    with patch('src.api.scheduler.task_scheduler.TrendRadarApp'):
        await scheduler.start()

        # 暂停任务
        success = await scheduler.pause_job()
        assert success is True

        # 恢复任务
        success = await scheduler.resume_job()
        assert success is True

        await scheduler.stop()


@pytest.mark.asyncio
async def test_trigger_now(scheduler):
    """测试立即触发任务"""
    with patch('src.api.scheduler.task_scheduler.TrendRadarApp') as MockApp:
        mock_app = Mock()
        mock_app.run.return_value = True
        MockApp.return_value = mock_app

        # 测试使用默认模式触发
        await scheduler.trigger_now()
        assert len(scheduler.execution_history) == 1

        # 测试指定模式触发
        await scheduler.trigger_now(mode="current")
        assert len(scheduler.execution_history) == 2
        assert scheduler.execution_history[-1]["mode"] == "current"


@pytest.mark.asyncio
async def test_execution_history_limit(scheduler):
    """测试执行历史记录数量限制"""
    scheduler.max_history_size = 3

    # 添加超过限制的记录
    for i in range(5):
        scheduler._record_execution(
            task_id=f"test_{i}",
            mode="daily",
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=1.0,
            success=True
        )

    # 应该只保留最新的 3 条
    assert len(scheduler.execution_history) == 3
    assert scheduler.execution_history[0]["task_id"] == "test_2"
    assert scheduler.execution_history[-1]["task_id"] == "test_4"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
