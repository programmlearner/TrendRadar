# coding=utf-8
"""测试 NewsReporter 的合并逻辑"""

import pytest
from pathlib import Path
from src.core.reporter import NewsReporter


@pytest.fixture
def reporter():
    """创建报告生成器实例"""
    return NewsReporter(rank_threshold=10)


@pytest.fixture
def sample_summary_file(tmp_path):
    """创建示例汇总文件"""
    summary_file = tmp_path / "当日汇总.txt"
    content = """人工智能 (共2条)

[知乎] GPT-5 即将发布 [1] - 15时30分 (1次) [URL:https://example.com/1] [MOBILE:https://m.example.com/1]
[微博] AI 技术突破 [5] - 15时30分 (1次) [URL:https://example.com/2] [MOBILE:https://m.example.com/2]

区块链 (共1条)

[百度热搜] 比特币价格暴涨 [3] - 15时30分 (1次) [URL:https://example.com/3] [MOBILE:https://m.example.com/3]

==== 以下ID请求失败 ====
douyin, toutiao
"""
    summary_file.write_text(content, encoding="utf-8")
    return summary_file


class TestParsExistingSummary:
    """测试解析现有汇总文件"""

    def test_parse_valid_summary(self, reporter, sample_summary_file):
        """测试解析有效的汇总文件"""
        result = reporter._parse_existing_summary(sample_summary_file)

        assert "stats" in result
        assert "failed_ids" in result

        # 检查词组
        assert "人工智能" in result["stats"]
        assert "区块链" in result["stats"]

        # 检查标题
        ai_stats = result["stats"]["人工智能"]
        assert "GPT-5 即将发布" in ai_stats
        assert "AI 技术突破" in ai_stats

        # 检查标题数据
        gpt5_data = ai_stats["GPT-5 即将发布"]
        assert gpt5_data["platform_name"] == "知乎"
        assert gpt5_data["ranks"] == [1]
        assert gpt5_data["count"] == 1
        assert gpt5_data["url"] == "https://example.com/1"
        assert gpt5_data["mobile_url"] == "https://m.example.com/1"

        # 检查失败ID
        assert set(result["failed_ids"]) == {"douyin", "toutiao"}

    def test_parse_empty_file(self, reporter, tmp_path):
        """测试解析空文件"""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("", encoding="utf-8")

        result = reporter._parse_existing_summary(empty_file)
        assert result["stats"] == {}
        assert result["failed_ids"] == []

    def test_parse_nonexistent_file(self, reporter, tmp_path):
        """测试解析不存在的文件"""
        nonexistent_file = tmp_path / "nonexistent.txt"

        result = reporter._parse_existing_summary(nonexistent_file)
        assert result["stats"] == {}
        assert result["failed_ids"] == []


class TestMergeReportData:
    """测试合并报告数据"""

    def test_merge_new_titles_only(self, reporter):
        """测试仅有新标题的合并"""
        existing_data = {
            "stats": {
                "人工智能": {
                    "GPT-5 即将发布": {
                        "platform_name": "知乎",
                        "url": "https://example.com/1",
                        "mobile_url": "https://m.example.com/1",
                        "ranks": [1],
                        "count": 1,
                        "time_display": "15时30分",
                    }
                }
            },
            "failed_ids": ["douyin"],
        }

        new_report_data = {
            "stats": [
                {
                    "word": "人工智能",
                    "count": 1,
                    "percentage": 100.0,
                    "titles": [
                        {
                            "title": "Claude 3.5 发布",
                            "platform": "weibo",
                            "source_name": "微博",
                            "time_display": "16时00分",
                            "count": 1,
                            "ranks": [2],
                            "rank_threshold": 10,
                            "url": "https://example.com/new",
                            "mobile_url": "https://m.example.com/new",
                            "is_new": True,
                        }
                    ],
                }
            ],
            "new_titles": [],
            "failed_ids": [],
            "total_new_count": 1,
        }

        merged = reporter._merge_report_data(existing_data, new_report_data)

        # 检查合并结果
        assert len(merged["stats"]) == 1
        ai_stat = merged["stats"][0]
        assert ai_stat["word"] == "人工智能"
        assert ai_stat["count"] == 2  # 1 现有 + 1 新增

        # 检查标题列表
        titles = {t["title"]: t for t in ai_stat["titles"]}
        assert "GPT-5 即将发布" in titles
        assert "Claude 3.5 发布" in titles

    def test_merge_duplicate_titles(self, reporter):
        """测试合并重复标题"""
        existing_data = {
            "stats": {
                "人工智能": {
                    "GPT-5 即将发布": {
                        "platform_name": "知乎",
                        "url": "https://example.com/1",
                        "mobile_url": "https://m.example.com/1",
                        "ranks": [1],
                        "count": 1,
                        "time_display": "15时30分",
                    }
                }
            },
            "failed_ids": [],
        }

        new_report_data = {
            "stats": [
                {
                    "word": "人工智能",
                    "count": 1,
                    "percentage": 100.0,
                    "titles": [
                        {
                            "title": "GPT-5 即将发布",  # 重复标题
                            "platform": "zhihu",
                            "source_name": "知乎",
                            "time_display": "16时00分",
                            "count": 1,
                            "ranks": [2],  # 新排名
                            "rank_threshold": 10,
                            "url": "https://example.com/1",
                            "mobile_url": "https://m.example.com/1",
                            "is_new": False,
                        }
                    ],
                }
            ],
            "new_titles": [],
            "failed_ids": [],
            "total_new_count": 0,
        }

        merged = reporter._merge_report_data(existing_data, new_report_data)

        # 检查合并结果
        ai_stat = merged["stats"][0]
        assert ai_stat["count"] == 1  # 仍然是 1 条（去重）

        # 检查标题数据
        title_data = ai_stat["titles"][0]
        assert title_data["title"] == "GPT-5 即将发布"
        assert title_data["count"] == 2  # 出现次数累加: 1 + 1
        assert set(title_data["ranks"]) == {1, 2}  # 排名合并

    def test_merge_failed_ids(self, reporter):
        """测试合并失败ID"""
        existing_data = {
            "stats": {},
            "failed_ids": ["douyin", "toutiao"],
        }

        new_report_data = {
            "stats": [],
            "new_titles": [],
            "failed_ids": ["toutiao", "bilibili"],  # 部分重复
            "total_new_count": 0,
        }

        merged = reporter._merge_report_data(existing_data, new_report_data)

        # 检查失败ID合并（去重）
        assert set(merged["failed_ids"]) == {"douyin", "toutiao", "bilibili"}


class TestGenerateMergedTextReport:
    """测试生成合并后的文本报告"""

    def test_first_generation(self, reporter, tmp_path, monkeypatch):
        """测试首次生成（无现有文件）"""
        # 修改输出路径
        def mock_get_output_path(output_type, filename):
            return tmp_path / filename

        monkeypatch.setattr(reporter, "get_output_path", mock_get_output_path)

        new_report_data = {
            "stats": [
                {
                    "word": "人工智能",
                    "count": 1,
                    "percentage": 100.0,
                    "titles": [
                        {
                            "title": "GPT-5 即将发布",
                            "platform": "zhihu",
                            "source_name": "知乎",
                            "time_display": "15时30分",
                            "count": 1,
                            "ranks": [1],
                            "rank_threshold": 10,
                            "url": "https://example.com/1",
                            "mobile_url": "https://m.example.com/1",
                            "is_new": True,
                        }
                    ],
                }
            ],
            "new_titles": [],
            "failed_ids": [],
            "total_new_count": 1,
        }

        file_path = tmp_path / "当日汇总.txt"

        # 首次生成（文件不存在）
        result_path = reporter._generate_merged_text_report(file_path, new_report_data)

        assert result_path.exists()
        content = result_path.read_text(encoding="utf-8")

        # 验证内容
        assert "人工智能 (共1条)" in content
        assert "GPT-5 即将发布" in content
        assert "[知乎]" in content
        assert "[1]" in content

    def test_merge_with_existing_file(self, reporter, sample_summary_file):
        """测试与现有文件合并"""
        new_report_data = {
            "stats": [
                {
                    "word": "人工智能",
                    "count": 1,
                    "percentage": 100.0,
                    "titles": [
                        {
                            "title": "GPT-5 即将发布",  # 重复标题
                            "platform": "zhihu",
                            "source_name": "知乎",
                            "time_display": "16时00分",
                            "count": 1,
                            "ranks": [2],
                            "rank_threshold": 10,
                            "url": "https://example.com/1",
                            "mobile_url": "https://m.example.com/1",
                            "is_new": False,
                        }
                    ],
                }
            ],
            "new_titles": [],
            "failed_ids": ["jin10"],  # 新失败ID
            "total_new_count": 0,
        }

        result_path = reporter._generate_merged_text_report(
            sample_summary_file, new_report_data
        )

        content = result_path.read_text(encoding="utf-8")

        # 验证合并结果
        assert "GPT-5 即将发布" in content
        assert "(2次)" in content  # 出现次数累加
        assert "[1 - 2]" in content  # 排名合并

        # 验证失败ID合并
        assert "douyin" in content
        assert "toutiao" in content
        assert "jin10" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
