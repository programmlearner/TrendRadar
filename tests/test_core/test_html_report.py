# coding=utf-8
"""HTML 报告生成测试"""

import os
from pathlib import Path
from src.core.reporter import NewsReporter
from src.models.news import News, WordGroupStatistic


def test_generate_html_report(tmp_path):
    """测试生成邮件专用的 HTML 报告"""
    # 准备测试数据
    news1 = News(
        title="测试新闻1",
        url="https://example.com/1",
        platform="zhihu",
        platform_name="知乎",
        rank=1,
        extra={"time_display": "1小时前", "count": 2, "all_ranks": [1, 2], "is_new": True}
    )
    news2 = News(
        title="测试新闻2",
        url="https://example.com/2",
        platform="weibo",
        platform_name="微博",
        rank=5,
        extra={"time_display": "2小时前", "count": 1, "all_ranks": [5], "is_new": False}
    )

    stat = WordGroupStatistic(
        word="测试关键词",
        count=2,
        percentage=100.0,
        news_list=[news1, news2]
    )

    # 创建临时输出目录
    output_dir = tmp_path / "output"
    os.makedirs(output_dir / "html", exist_ok=True)

    # 修改 NewsReporter 的输出路径
    reporter = NewsReporter(rank_threshold=10)
    original_get_output_path = reporter.get_output_path

    def mock_get_output_path(output_type: str, filename: str):
        return output_dir / output_type / filename

    reporter.get_output_path = mock_get_output_path

    # 生成 HTML 报告
    html_path = reporter.generate_html_report(
        stats=[stat],
        total_titles=2,
        failed_ids=["douyin"],
        new_news_list=[news1],
        mode="daily",
        is_daily_summary=True
    )

    # 验证文件生成
    assert html_path.exists()
    assert html_path.name == "email_report_daily.html"

    # 读取 HTML 内容
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 验证 HTML 内容
    assert "<!DOCTYPE html>" in html_content
    assert "TrendRadar" in html_content
    assert "测试关键词" in html_content
    assert "测试新闻1" in html_content
    assert "测试新闻2" in html_content
    assert "知乎" in html_content
    assert "微博" in html_content
    # URL 会被 HTML 转义，检查转义后的内容
    assert ("https://example.com/1" in html_content or
            "https:&#x2F;&#x2F;example.com&#x2F;1" in html_content or
            "example.com" in html_content)
    assert "当日汇总" in html_content
    assert "douyin" in html_content  # 失败的平台ID

    # 验证内联样式（邮件客户端兼容）
    assert "style=" in html_content

    # 验证无 JavaScript 依赖
    assert "<script" not in html_content

    # 验证新增标记
    assert "🆕" in html_content or "is_new" in html_content

    print(f"✓ HTML 报告生成成功: {html_path}")


def test_html_report_different_modes(tmp_path):
    """测试不同模式下的 HTML 文件名"""
    news = News(
        title="测试",
        url="https://example.com",
        platform="zhihu",
        platform_name="知乎",
        rank=1
    )

    stat = WordGroupStatistic(
        word="测试",
        count=1,
        percentage=100.0,
        news_list=[news]
    )

    output_dir = tmp_path / "output"
    os.makedirs(output_dir / "html", exist_ok=True)

    reporter = NewsReporter()

    def mock_get_output_path(output_type: str, filename: str):
        return output_dir / output_type / filename

    reporter.get_output_path = mock_get_output_path

    # 测试 daily 模式
    html_daily = reporter.generate_html_report(
        stats=[stat], total_titles=1, mode="daily", is_daily_summary=True
    )
    assert html_daily.name == "email_report_daily.html"

    # 测试 current 模式
    html_current = reporter.generate_html_report(
        stats=[stat], total_titles=1, mode="current", is_daily_summary=True
    )
    assert html_current.name == "email_report_current.html"

    # 测试 incremental 模式
    html_incremental = reporter.generate_html_report(
        stats=[stat], total_titles=1, mode="incremental", is_daily_summary=True
    )
    assert html_incremental.name == "email_report_incremental.html"


def test_html_special_characters_escaping(tmp_path):
    """测试 HTML 特殊字符转义"""
    news = News(
        title='测试<script>alert("XSS")</script>',
        url="https://example.com?a=1&b=2",
        platform="zhihu",
        platform_name='知乎<>"&',
        rank=1
    )

    stat = WordGroupStatistic(
        word="测试&转义",
        count=1,
        percentage=100.0,
        news_list=[news]
    )

    output_dir = tmp_path / "output"
    os.makedirs(output_dir / "html", exist_ok=True)

    reporter = NewsReporter()

    def mock_get_output_path(output_type: str, filename: str):
        return output_dir / output_type / filename

    reporter.get_output_path = mock_get_output_path

    html_path = reporter.generate_html_report(
        stats=[stat], total_titles=1, mode="daily", is_daily_summary=True
    )

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 验证特殊字符已转义
    assert "&lt;script&gt;" in html_content or "script" not in html_content.lower()
    assert "&amp;" in html_content or "a=1&amp;b=2" in html_content
    assert "&quot;" in html_content or "&lt;" in html_content


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
