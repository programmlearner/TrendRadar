# coding=utf-8
"""新闻报告生成模块"""

import os
import json
import tempfile
from pathlib import Path
from string import Template
from typing import List, Dict, Optional, Any, Tuple

from src.models.news import News, WordGroupStatistic
from src.utils.file import clean_title, html_escape
from src.utils.time import format_time_filename, format_date_folder

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
EMAIL_TEMPLATE_PATH = TEMPLATES_DIR / "email_report_template.html"
EMAIL_HERO_TAGLINE = "汇集 11+ 平台热点，实时洞察关键词组合与新增动向。"
MODE_METADATA = {
    "daily": {
        "label": "当日汇总",
        "description": "聚焦当日跨平台关键词热度与走势"
    },
    "current": {
        "label": "当前榜单",
        "description": "高频监控当前榜单并及时预警波动"
    },
    "incremental": {
        "label": "增量监控",
        "description": "仅推送新增热点，辅助实时决策"
    }
}


class NewsReporter:
    """新闻报告生成器

    负责：
    - 准备报告数据
    - 格式化标题
    - 生成各种格式的报告（HTML、文本等）
    """

    def __init__(self, rank_threshold: int = 10):
        """初始化报告生成器

        Args:
            rank_threshold: 排名阈值（用于高亮显示）
        """
        self.rank_threshold = rank_threshold
        self._email_template_cache: Optional[str] = None

    def prepare_report_data(
        self,
        stats: List[WordGroupStatistic],
        failed_ids: Optional[List[str]] = None,
        new_news_list: Optional[List[News]] = None,
        mode: str = "daily"
    ) -> Dict:
        """准备报告数据

        Args:
            stats: 词组统计列表
            failed_ids: 失败的平台ID列表
            new_news_list: 新增新闻列表
            mode: 模式 (daily/current/incremental)

        Returns:
            Dict: 报告数据字典
        """
        # 在增量模式下隐藏新增新闻区域
        hide_new_section = mode == "incremental"

        # 处理新增新闻
        processed_new_titles = []
        if not hide_new_section and new_news_list:
            # 按平台分组
            new_by_platform = {}
            for news in new_news_list:
                platform_name = news.platform_name
                if platform_name not in new_by_platform:
                    new_by_platform[platform_name] = []
                new_by_platform[platform_name].append(news)

            for platform_name, news_list in new_by_platform.items():
                source_titles = []
                for news in news_list:
                    processed_title = {
                        "title": news.title,
                        "platform": news.platform,  # 平台ID
                        "source_name": news.platform_name,
                        "time_display": "",
                        "count": 1,
                        "ranks": [news.rank],
                        "rank_threshold": self.rank_threshold,
                        "url": news.url,
                        "mobile_url": news.mobile_url or "",
                        "is_new": True,
                    }
                    source_titles.append(processed_title)

                if source_titles:
                    processed_new_titles.append({
                        "source_id": news.platform,
                        "source_name": platform_name,
                        "titles": source_titles,
                    })

        # 处理统计数据
        processed_stats = []
        for stat in stats:
            if stat.count <= 0:
                continue

            processed_titles = []
            for news in stat.news_list:
                # 从extra中获取信息
                extra = news.extra
                processed_title = {
                    "title": news.title,
                    "platform": news.platform,  # 平台ID
                    "source_name": news.platform_name,
                    "time_display": extra.get("time_display", ""),
                    "count": extra.get("count", 1),
                    "ranks": extra.get("all_ranks", [news.rank]),
                    "rank_threshold": self.rank_threshold,
                    "url": news.url,
                    "mobile_url": extra.get("mobileUrl", ""),
                    "is_new": extra.get("is_new", False),
                }
                processed_titles.append(processed_title)

            processed_stats.append({
                "word": stat.word,
                "count": stat.count,
                "percentage": stat.percentage,
                "titles": processed_titles,
            })

        return {
            "stats": processed_stats,
            "new_titles": processed_new_titles,
            "failed_ids": failed_ids or [],
            "total_new_count": sum(
                len(source["titles"]) for source in processed_new_titles
            ),
        }

    def format_rank_display(
        self,
        ranks: List[int],
        rank_threshold: int,
        format_type: str
    ) -> str:
        """统一的排名格式化方法

        Args:
            ranks: 排名列表
            rank_threshold: 排名阈值
            format_type: 格式类型 (html/feishu/dingtalk/wework/telegram/ntfy)

        Returns:
            str: 格式化后的排名显示
        """
        if not ranks:
            return ""

        unique_ranks = sorted(set(ranks))
        min_rank = unique_ranks[0]
        max_rank = unique_ranks[-1]

        # 根据平台选择高亮格式
        if format_type == "html":
            highlight_start = "<font color='red'><strong>"
            highlight_end = "</strong></font>"
        elif format_type == "feishu":
            highlight_start = "<font color='red'>**"
            highlight_end = "**</font>"
        elif format_type in ["dingtalk", "wework"]:
            highlight_start = "**"
            highlight_end = "**"
        elif format_type == "telegram":
            highlight_start = "<b>"
            highlight_end = "</b>"
        else:
            highlight_start = "**"
            highlight_end = "**"

        # 判断是否高亮
        is_highlight = min_rank <= rank_threshold

        if min_rank == max_rank:
            rank_text = f"[{min_rank}]"
        else:
            rank_text = f"[{min_rank} - {max_rank}]"

        if is_highlight:
            return f"{highlight_start}{rank_text}{highlight_end}"
        else:
            return rank_text

    def format_title_for_platform(
        self,
        platform: str,
        title_data: Dict,
        show_source: bool = True
    ) -> str:
        """统一的标题格式化方法

        Args:
            platform: 平台类型 (feishu/dingtalk/wework/telegram/ntfy/html)
            title_data: 标题数据字典
            show_source: 是否显示来源平台

        Returns:
            str: 格式化后的标题
        """
        rank_display = self.format_rank_display(
            title_data["ranks"],
            title_data["rank_threshold"],
            platform
        )

        link_url = title_data["mobile_url"] or title_data["url"]
        cleaned_title = clean_title(title_data["title"])
        title_prefix = "🆕 " if title_data.get("is_new") else ""

        if platform == "feishu":
            return self._format_feishu(
                cleaned_title, link_url, title_prefix, title_data, rank_display, show_source
            )
        elif platform == "dingtalk":
            return self._format_dingtalk(
                cleaned_title, link_url, title_prefix, title_data, rank_display, show_source
            )
        elif platform == "wework":
            return self._format_wework(
                cleaned_title, link_url, title_prefix, title_data, rank_display, show_source
            )
        elif platform == "telegram":
            return self._format_telegram(
                cleaned_title, link_url, title_prefix, title_data, rank_display, show_source
            )
        elif platform == "ntfy":
            return self._format_ntfy(
                cleaned_title, link_url, title_prefix, title_data, rank_display, show_source
            )
        elif platform == "html":
            return self._format_html(
                cleaned_title, link_url, title_data, rank_display
            )
        else:
            return cleaned_title

    def _format_feishu(
        self,
        title: str,
        link_url: str,
        prefix: str,
        data: Dict,
        rank_display: str,
        show_source: bool
    ) -> str:
        """飞书格式"""
        if link_url:
            formatted_title = f"[{title}]({link_url})"
        else:
            formatted_title = title

        if show_source:
            result = f"<font color='grey'>[{data['source_name']}]</font> {prefix}{formatted_title}"
        else:
            result = f"{prefix}{formatted_title}"

        if rank_display:
            result += f" {rank_display}"
        if data["time_display"]:
            result += f" <font color='grey'>- {data['time_display']}</font>"
        if data["count"] > 1:
            result += f" <font color='green'>({data['count']}次)</font>"

        return result

    def _format_dingtalk(
        self,
        title: str,
        link_url: str,
        prefix: str,
        data: Dict,
        rank_display: str,
        show_source: bool
    ) -> str:
        """钉钉格式"""
        if link_url:
            formatted_title = f"[{title}]({link_url})"
        else:
            formatted_title = title

        if show_source:
            result = f"[{data['source_name']}] {prefix}{formatted_title}"
        else:
            result = f"{prefix}{formatted_title}"

        if rank_display:
            result += f" {rank_display}"
        if data["time_display"]:
            result += f" - {data['time_display']}"
        if data["count"] > 1:
            result += f" ({data['count']}次)"

        return result

    def _format_wework(
        self,
        title: str,
        link_url: str,
        prefix: str,
        data: Dict,
        rank_display: str,
        show_source: bool
    ) -> str:
        """企业微信格式"""
        return self._format_dingtalk(title, link_url, prefix, data, rank_display, show_source)

    def _format_telegram(
        self,
        title: str,
        link_url: str,
        prefix: str,
        data: Dict,
        rank_display: str,
        show_source: bool
    ) -> str:
        """Telegram格式"""
        if link_url:
            formatted_title = f'<a href="{link_url}">{html_escape(title)}</a>'
        else:
            formatted_title = title

        if show_source:
            result = f"[{data['source_name']}] {prefix}{formatted_title}"
        else:
            result = f"{prefix}{formatted_title}"

        if rank_display:
            result += f" {rank_display}"
        if data["time_display"]:
            result += f" <code>- {data['time_display']}</code>"
        if data["count"] > 1:
            result += f" <code>({data['count']}次)</code>"

        return result

    def _format_ntfy(
        self,
        title: str,
        link_url: str,
        prefix: str,
        data: Dict,
        rank_display: str,
        show_source: bool
    ) -> str:
        """ntfy格式"""
        if link_url:
            formatted_title = f"[{title}]({link_url})"
        else:
            formatted_title = title

        if show_source:
            result = f"[{data['source_name']}] {prefix}{formatted_title}"
        else:
            result = f"{prefix}{formatted_title}"

        if rank_display:
            result += f" {rank_display}"
        if data["time_display"]:
            result += f" `- {data['time_display']}`"
        if data["count"] > 1:
            result += f" `({data['count']}次)`"

        return result

    def _format_html(
        self,
        title: str,
        link_url: str,
        data: Dict,
        rank_display: str
    ) -> str:
        """HTML格式"""
        escaped_title = html_escape(title)
        escaped_source_name = html_escape(data["source_name"])

        if link_url:
            escaped_url = html_escape(link_url)
            formatted_title = f'[{escaped_source_name}] <a href="{escaped_url}" target="_blank" class="news-link">{escaped_title}</a>'
        else:
            formatted_title = f'[{escaped_source_name}] <span class="no-link">{escaped_title}</span>'

        if rank_display:
            formatted_title += f" {rank_display}"
        if data["time_display"]:
            escaped_time = html_escape(data["time_display"])
            formatted_title += f" <font color='grey'>- {escaped_time}</font>"
        if data["count"] > 1:
            formatted_title += f" <font color='green'>({data['count']}次)</font>"

        if data.get("is_new"):
            formatted_title = f"<div class='new-title'>🆕 {formatted_title}</div>"

        return formatted_title

    def get_output_path(self, output_type: str, filename: str) -> Path:
        """获取输出文件路径

        Args:
            output_type: 输出类型 (html/txt)
            filename: 文件名

        Returns:
            Path: 文件路径
        """
        date_folder = format_date_folder()
        output_dir = Path("output") / date_folder / output_type
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir / filename

    def generate_text_report(
        self,
        stats: List[WordGroupStatistic],
        total_titles: int,
        failed_ids: Optional[List[str]] = None,
        new_news_list: Optional[List[News]] = None,
        mode: str = "daily",
        is_daily_summary: bool = False
    ) -> Path:
        """生成文本报告

        Args:
            stats: 词组统计列表
            total_titles: 总标题数
            failed_ids: 失败的平台ID列表
            new_news_list: 新增新闻列表
            mode: 模式
            is_daily_summary: 是否为当日汇总

        Returns:
            Path: 生成的文件路径
        """
        # 使用固定文件名,便于读取和增量对比
        if is_daily_summary:
            if mode == "current":
                filename = "当前榜单汇总.txt"
            elif mode == "incremental":
                filename = "当日增量.txt"
            else:
                filename = "当日汇总.txt"
        else:
            filename = f"{format_time_filename()}.txt"

        file_path = self.get_output_path("txt", filename)

        report_data = self.prepare_report_data(stats, failed_ids, new_news_list, mode)

        # 如果是 "当日汇总.txt" 且文件已存在，使用追加合并模式
        if filename == "当日汇总.txt" and file_path.exists():
            print(f"ℹ️  检测到现有汇总文件，使用追加合并模式")
            return self._generate_merged_text_report(file_path, report_data)

        content_lines = []

        # 写入词组统计
        for stat in report_data["stats"]:
            content_lines.append(f"{stat['word']} (共{stat['count']}条)")
            content_lines.append("")

            for title_data in stat["titles"]:
                # 简单的文本格式
                line = f"[{title_data['source_name']}] {title_data['title']}"
                if title_data["ranks"]:
                    min_rank = min(title_data["ranks"])
                    max_rank = max(title_data["ranks"])
                    if min_rank == max_rank:
                        line += f" [{min_rank}]"
                    else:
                        line += f" [{min_rank} - {max_rank}]"
                if title_data["time_display"]:
                    line += f" - {title_data['time_display']}"
                if title_data["count"] > 1:
                    line += f" ({title_data['count']}次)"
                if title_data["url"]:
                    line += f" [URL:{title_data['url']}]"
                if title_data["mobile_url"]:
                    line += f" [MOBILE:{title_data['mobile_url']}]"

                content_lines.append(line)

            content_lines.append("")

        # 写入新增新闻
        if report_data["new_titles"]:
            content_lines.append("==== 最新批次新增 ====")
            content_lines.append("")

            for source_data in report_data["new_titles"]:
                content_lines.append(f"{source_data['source_name']} (新增{len(source_data['titles'])}条)")
                content_lines.append("")

                for title_data in source_data["titles"]:
                    line = f"{title_data['title']}"
                    if title_data["ranks"]:
                        line += f" [{title_data['ranks'][0]}]"
                    if title_data["url"]:
                        line += f" [URL:{title_data['url']}]"
                    if title_data["mobile_url"]:
                        line += f" [MOBILE:{title_data['mobile_url']}]"

                    content_lines.append(line)

                content_lines.append("")

        # 写入失败信息
        if report_data["failed_ids"]:
            content_lines.append("==== 以下ID请求失败 ====")
            content_lines.append(", ".join(report_data["failed_ids"]))

        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))

        return file_path

    def generate_json_report(
        self,
        stats: List[WordGroupStatistic],
        total_titles: int,
        failed_ids: Optional[List[str]] = None,
        new_news_list: Optional[List[News]] = None,
        mode: str = "daily",
        is_daily_summary: bool = False  # pylint: disable=unused-argument
    ) -> Path:
        """生成 JSON 报告(全量覆写模式)

        Args:
            stats: 词组统计列表
            total_titles: 总标题数
            failed_ids: 失败的平台ID列表
            new_news_list: 新增新闻列表
            mode: 模式
            is_daily_summary: 是否为当日汇总

        Returns:
            Path: JSON 文件路径
        """
        # 准备报告数据
        report_data = self.prepare_report_data(stats, failed_ids, new_news_list, mode)

        # 构建完整 JSON 数据
        json_data = self._build_full_json_data(
            report_data=report_data,
            total_titles=total_titles,
            mode=mode
        )

        # 获取文件路径
        json_path = self.get_output_path("json", "news_summary.json")

        # 原子写入
        self._atomic_write_json(json_path, json_data)

        return json_path

    def _build_full_json_data(
        self,
        report_data: Dict,
        total_titles: int,  # pylint: disable=unused-argument
        mode: str
    ) -> Dict[str, Any]:
        """构建完整 JSON 数据(包含所有匹配新闻)

        Args:
            report_data: prepare_report_data() 返回的数据
            total_titles: 总新闻数
            mode: 运行模式

        Returns:
            Dict: 完整 JSON 数据结构
        """
        from src.utils.time import get_beijing_time

        now = get_beijing_time()

        # 转换词组统计数据(包含所有新闻,不过滤 is_new)
        stats_list = []
        total_count = 0

        for stat in report_data["stats"]:
            news_list = []
            for title_data in stat["titles"]:
                news_item = {
                    "title": title_data["title"],
                    "url": title_data["url"],
                    "mobile_url": title_data["mobile_url"],
                    "platform": title_data["platform"],
                    "platform_name": title_data["source_name"],
                    "rank": min(title_data["ranks"]) if title_data["ranks"] else 999,
                    "ranks": title_data["ranks"],
                    "occurrence_count": title_data["count"],
                    "time_display": title_data["time_display"],
                }
                news_list.append(news_item)

            if news_list:
                total_count += len(news_list)
                stats_list.append({
                    "word_group": stat["word"],
                    "count": len(news_list),
                    "percentage": stat["percentage"],
                    "news_list": news_list,
                })

        return {
            "metadata": {
                "date": now.strftime("%Y-%m-%d"),
                "mode": mode,
                "timestamp": now.isoformat(),
                "total_word_groups": len(stats_list),
                "total_news_count": total_count,
            },
            "stats": stats_list,
        }

    def _atomic_write_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        """原子写入 JSON 文件

        先写入临时文件,成功后再重命名,防止写入失败导致数据丢失。

        Args:
            file_path: 目标文件路径
            data: 要写入的数据
        """
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建临时文件(在同一目录下,确保原子 rename)
        fd, temp_path = tempfile.mkstemp(
            dir=file_path.parent,
            prefix=".tmp_",
            suffix=".json"
        )

        try:
            # 写入临时文件
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 原子重命名
            os.replace(temp_path, file_path)
        except Exception as e:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except:
                pass
            raise e

    def _parse_existing_summary(self, file_path: Path) -> Dict[str, Any]:
        """解析现有的汇总文件

        Args:
            file_path: 文件路径

        Returns:
            Dict: 解析后的数据结构
                {
                    "stats": {word_group: {title: title_data}},
                    "failed_ids": [...]
                }
        """
        existing_stats = {}
        failed_ids = []
        current_word_group = None
        in_failed_section = False

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    if not line:
                        continue

                    # 检测失败ID区域开始
                    if line.startswith("==== 以下ID请求失败 ===="):
                        in_failed_section = True
                        current_word_group = None  # 退出词组区域
                        continue

                    # 检测新增新闻区域（结束词组统计区域）
                    if line.startswith("==== 最新批次新增 ===="):
                        current_word_group = None
                        in_failed_section = False
                        continue

                    # 如果在失败ID区域，解析失败ID
                    if in_failed_section:
                        if ',' in line:
                            failed_ids = [id.strip() for id in line.split(',') if id.strip()]
                        continue

                    # 检测词组标题行: "词组名 (共N条)"
                    if line.endswith('条)') and ' (共' in line:
                        # 提取词组名
                        current_word_group = line.split(' (共')[0]
                        if current_word_group not in existing_stats:
                            existing_stats[current_word_group] = {}
                        continue

                    # 解析标题行: "[平台名] 标题 [排名] - 时间 [URL:...] [MOBILE:...]"
                    if line.startswith('[') and '] ' in line and current_word_group:
                        try:
                            # 提取平台名称
                            platform_end = line.index('] ')
                            platform_name = line[1:platform_end]
                            rest = line[platform_end + 2:]

                            # 提取 MOBILE URL
                            mobile_url = ""
                            if " [MOBILE:" in rest:
                                rest, mobile_part = rest.rsplit(" [MOBILE:", 1)
                                if mobile_part.endswith("]"):
                                    mobile_url = mobile_part[:-1]

                            # 提取 URL
                            url = ""
                            if " [URL:" in rest:
                                rest, url_part = rest.rsplit(" [URL:", 1)
                                if url_part.endswith("]"):
                                    url = url_part[:-1]

                            # 提取次数信息 "(N次)"
                            count = 1
                            if " (" in rest and "次)" in rest:
                                rest, count_part = rest.rsplit(" (", 1)
                                if count_part.endswith("次)"):
                                    count_str = count_part[:-2]
                                    if count_str.isdigit():
                                        count = int(count_str)

                            # 提取时间信息 "- 时间"
                            time_display = ""
                            if " - " in rest:
                                title_rank_part, time_display = rest.rsplit(" - ", 1)
                                rest = title_rank_part

                            # 提取排名 "[排名]" 或 "[min - max]"
                            ranks = []
                            if " [" in rest and "]" in rest:
                                title_part, rank_part = rest.rsplit(" [", 1)
                                if rank_part.endswith("]"):
                                    rank_str = rank_part[:-1]
                                    if " - " in rank_str:
                                        # 范围排名
                                        min_rank, max_rank = rank_str.split(" - ")
                                        if min_rank.isdigit() and max_rank.isdigit():
                                            ranks = list(range(int(min_rank), int(max_rank) + 1))
                                    elif rank_str.isdigit():
                                        ranks = [int(rank_str)]
                                rest = title_part

                            title = rest.strip()

                            # 存储标题数据
                            if title not in existing_stats[current_word_group]:
                                existing_stats[current_word_group][title] = {
                                    "platform_name": platform_name,
                                    "url": url,
                                    "mobile_url": mobile_url,
                                    "ranks": ranks,
                                    "count": count,
                                    "time_display": time_display,
                                }

                        except Exception as e:
                            print(f"⚠️  解析标题行失败: {line[:50]}... 错误: {e}")
                            continue

        except Exception as e:
            print(f"⚠️  读取汇总文件失败: {e}")

        return {
            "stats": existing_stats,
            "failed_ids": failed_ids,
        }

    def _merge_report_data(
        self,
        existing_data: Dict[str, Any],
        new_report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """合并现有数据和新数据

        Args:
            existing_data: 从文件解析的现有数据
            new_report_data: 新的报告数据 (prepare_report_data 返回)

        Returns:
            Dict: 合并后的报告数据
        """
        merged_stats = []
        existing_stats = existing_data.get("stats", {})

        # 处理每个新的词组统计
        for new_stat in new_report_data["stats"]:
            word_group = new_stat["word"]
            existing_titles = existing_stats.get(word_group, {})

            merged_titles = []
            seen_titles = set()

            # 1. 先处理新数据中的标题
            for new_title_data in new_stat["titles"]:
                title = new_title_data["title"]
                seen_titles.add(title)

                if title in existing_titles:
                    # 标题已存在，合并数据
                    existing_title_data = existing_titles[title]

                    # 合并排名
                    existing_ranks = existing_title_data.get("ranks", [])
                    new_ranks = new_title_data.get("ranks", [])
                    merged_ranks = sorted(set(existing_ranks + new_ranks))

                    # 更新出现次数
                    existing_count = existing_title_data.get("count", 1)
                    merged_count = existing_count + 1

                    # 使用新数据的其他信息
                    merged_title = new_title_data.copy()
                    merged_title["ranks"] = merged_ranks
                    merged_title["count"] = merged_count

                    # 如果现有数据有时间信息，保留
                    if existing_title_data.get("time_display"):
                        merged_title["time_display"] = existing_title_data["time_display"]

                    merged_titles.append(merged_title)
                else:
                    # 新标题，直接添加
                    merged_titles.append(new_title_data)

            # 2. 添加现有数据中未在新数据中出现的标题（历史标题）
            for existing_title, existing_title_data in existing_titles.items():
                if existing_title not in seen_titles:
                    # 转换为 report_data 格式
                    historical_title = {
                        "title": existing_title,
                        "platform": "",  # 历史数据可能缺少平台ID
                        "source_name": existing_title_data.get("platform_name", ""),
                        "time_display": existing_title_data.get("time_display", ""),
                        "count": existing_title_data.get("count", 1),
                        "ranks": existing_title_data.get("ranks", []),
                        "rank_threshold": self.rank_threshold,
                        "url": existing_title_data.get("url", ""),
                        "mobile_url": existing_title_data.get("mobile_url", ""),
                        "is_new": False,
                    }
                    merged_titles.append(historical_title)

            # 构建合并后的词组统计
            merged_stats.append({
                "word": word_group,
                "count": len(merged_titles),
                "percentage": 0,  # 稍后重新计算
                "titles": merged_titles,
            })

        # 重新计算百分比
        total_count = sum(stat["count"] for stat in merged_stats)
        if total_count > 0:
            for stat in merged_stats:
                stat["percentage"] = round(stat["count"] / total_count * 100, 2)

        # 合并失败ID
        existing_failed_ids = set(existing_data.get("failed_ids", []))
        new_failed_ids = set(new_report_data.get("failed_ids", []))
        merged_failed_ids = list(existing_failed_ids | new_failed_ids)

        return {
            "stats": merged_stats,
            "new_titles": new_report_data.get("new_titles", []),
            "failed_ids": merged_failed_ids,
            "total_new_count": new_report_data.get("total_new_count", 0),
        }

    def _generate_merged_text_report(
        self,
        file_path: Path,
        new_report_data: Dict[str, Any]
    ) -> Path:
        """生成合并后的文本报告

        Args:
            file_path: 文件路径
            new_report_data: 新的报告数据

        Returns:
            Path: 文件路径
        """
        # 1. 解析现有汇总文件
        existing_data = self._parse_existing_summary(file_path)

        # 2. 合并数据
        merged_data = self._merge_report_data(existing_data, new_report_data)

        # 3. 生成内容
        content_lines = []

        # 写入词组统计
        for stat in merged_data["stats"]:
            content_lines.append(f"{stat['word']} (共{stat['count']}条)")
            content_lines.append("")

            for title_data in stat["titles"]:
                # 简单的文本格式
                line = f"[{title_data['source_name']}] {title_data['title']}"
                if title_data["ranks"]:
                    min_rank = min(title_data["ranks"])
                    max_rank = max(title_data["ranks"])
                    if min_rank == max_rank:
                        line += f" [{min_rank}]"
                    else:
                        line += f" [{min_rank} - {max_rank}]"
                if title_data["time_display"]:
                    line += f" - {title_data['time_display']}"
                if title_data["count"] > 1:
                    line += f" ({title_data['count']}次)"
                if title_data["url"]:
                    line += f" [URL:{title_data['url']}]"
                if title_data["mobile_url"]:
                    line += f" [MOBILE:{title_data['mobile_url']}]"

                content_lines.append(line)

            content_lines.append("")

        # 写入新增新闻（如果有）
        if merged_data["new_titles"]:
            content_lines.append("==== 最新批次新增 ====")
            content_lines.append("")

            for source_data in merged_data["new_titles"]:
                content_lines.append(f"{source_data['source_name']} (新增{len(source_data['titles'])}条)")
                content_lines.append("")

                for title_data in source_data["titles"]:
                    line = f"{title_data['title']}"
                    if title_data["ranks"]:
                        line += f" [{title_data['ranks'][0]}]"
                    if title_data["url"]:
                        line += f" [URL:{title_data['url']}]"
                    if title_data["mobile_url"]:
                        line += f" [MOBILE:{title_data['mobile_url']}]"

                    content_lines.append(line)

                content_lines.append("")

        # 写入失败信息
        if merged_data["failed_ids"]:
            content_lines.append("==== 以下ID请求失败 ====")
            content_lines.append(", ".join(merged_data["failed_ids"]))

        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(content_lines))

        print(f"✓ 汇总文件已更新: {file_path.name}")
        return file_path

    def generate_html_report(
        self,
        stats: List[WordGroupStatistic],
        total_titles: int,
        failed_ids: Optional[List[str]] = None,
        new_news_list: Optional[List[News]] = None,
        mode: str = "daily",
        is_daily_summary: bool = False
    ) -> Path:
        """生成邮件专用的 HTML 报告（服务器端渲染，无 JS 依赖）

        Args:
            stats: 词组统计列表
            total_titles: 总标题数
            failed_ids: 失败的平台ID列表
            new_news_list: 新增新闻列表
            mode: 模式
            is_daily_summary: 是否为当日汇总

        Returns:
            Path: 生成的文件路径
        """
        # 使用固定文件名
        if is_daily_summary:
            if mode == "current":
                filename = "email_report_current.html"
            elif mode == "incremental":
                filename = "email_report_incremental.html"
            else:
                filename = "email_report_daily.html"
        else:
            filename = f"email_{format_time_filename()}.html"

        file_path = self.get_output_path("html", filename)

        # 准备报告数据
        report_data = self.prepare_report_data(stats, failed_ids, new_news_list, mode)

        # 生成 HTML 内容
        html_content = self._build_email_html(report_data, total_titles, mode)

        # 写入文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return file_path

    def _build_email_html(
        self,
        report_data: Dict,
        total_titles: int,
        mode: str
    ) -> str:
        """构建邮件专用的 HTML 内容（模板渲染）"""
        template = self._get_email_template()

        mode_info = MODE_METADATA.get(mode, {
            "label": mode or "自定义模式",
            "description": "自动生成热点报告"
        })
        mode_label = mode_info["label"]
        mode_description = mode_info["description"]

        from src.utils.time import get_beijing_time

        now = get_beijing_time()
        date_str = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        news_sections = self._render_word_groups(report_data.get("stats", []))
        new_section = self._render_new_section(
            report_data.get("new_titles", []),
            report_data.get("total_new_count", 0)
        )
        failed_section = self._render_failed_section(report_data.get("failed_ids", []))

        substitutions = {
            "page_title": f"TrendRadar - {mode_label} 报告",
            "mode_label": mode_label,
            "hero_tagline": EMAIL_HERO_TAGLINE,
            "meta_date": date_str,
            "meta_keywords": str(len(report_data.get("stats", []))),
            "meta_news": str(total_titles),
            "meta_updated": timestamp,
            "mode_description": mode_description,
            "news_sections": news_sections,
            "new_section": new_section,
            "failed_section": failed_section,
        }

        return template.safe_substitute(substitutions)

    def _get_email_template(self) -> Template:
        """读取并缓存 HTML 模板"""
        if self._email_template_cache is None:
            if not EMAIL_TEMPLATE_PATH.exists():
                raise FileNotFoundError(
                    f"模板文件不存在: {EMAIL_TEMPLATE_PATH}"
                )
            self._email_template_cache = EMAIL_TEMPLATE_PATH.read_text(
                encoding="utf-8"
            )
        return Template(self._email_template_cache)

    def _render_word_groups(self, stats: List[Dict[str, Any]]) -> str:
        """渲染词组统计区域（邮件安全版）"""
        if not stats:
            return self._render_empty_state()

        sections: List[str] = []
        for stat in stats:
            titles = stat.get("titles", [])
            body_rows = []
            for idx, title_data in enumerate(titles):
                body_rows.append(self._render_news_item(title_data, is_first=idx == 0))

            if not body_rows:
                body_rows.append(self._render_placeholder_item("该词组暂无可展示的新闻。"))

            percentage = stat.get("percentage")
            if isinstance(percentage, (int, float)):
                percentage_text = f"{percentage:.1f}% 覆盖"
            elif percentage is not None:
                percentage_text = f"{percentage}% 覆盖"
            else:
                percentage_text = ""

            meta_text = f"共 {stat.get('count', 0)} 条"
            if percentage_text:
                meta_text += f" · {percentage_text}"

            sections.append(self._wrap_card(
                title=html_escape(stat.get("word", "未命名词组")),
                meta_text=html_escape(meta_text),
                body_rows="".join(body_rows)
            ))

        return "".join(sections)

    def _render_news_item(self, title_data: Dict[str, Any], is_first: bool = False) -> str:
        """渲染单条新闻（内联样式）"""
        link_url = title_data.get("mobile_url") or title_data.get("url") or ""
        title_text = html_escape(title_data.get("title", "未命名标题"))

        if link_url:
            link_html = (
                f'<a href="{html_escape(link_url)}" '
                f'style="color:#0f6bff; text-decoration:none;">{title_text}</a>'
            )
        else:
            link_html = f'<span style="color:#111111;">{title_text}</span>'

        new_badge = ""
        if title_data.get("is_new"):
            new_badge = (
                '<span style="display:inline-block; padding:2px 8px; border-radius:999px; '
                'background-color:#e7f7ec; color:#0a8f08; font-size:11px; '
                'font-weight:600; margin-right:6px;">NEW</span>'
            )

        meta_parts: List[str] = []
        source_name = title_data.get("source_name")
        if source_name:
            meta_parts.append(f'<span>[{html_escape(source_name)}]</span>')

        rank_label, highlight = self._build_rank_chip(title_data.get("ranks", []))
        if rank_label:
            rank_color = "#c62828" if highlight else "#0f6bff"
            rank_bg = "#fdecef" if highlight else "#e6efff"
            meta_parts.append(
                f'<span style="display:inline-block; padding:2px 10px; border-radius:999px; '
                f'background-color:{rank_bg}; color:{rank_color}; font-size:12px; '
                f'font-weight:600;">{html_escape(rank_label)}</span>'
            )

        time_display = title_data.get("time_display")
        if time_display:
            meta_parts.append(f'<span>{html_escape(time_display)}</span>')

        count = title_data.get("count", 0)
        if count and count > 1:
            meta_parts.append(f'<span>{count} 次出现</span>')

        meta_block = ""
        if meta_parts:
            meta_block = (
                "<div style=\"font-size:13px; color:#6e6e73; margin-top:6px;\">"
                + " &middot; ".join(meta_parts)
                + "</div>"
            )

        border_style = "border-top:1px solid #f1f2f6;" if not is_first else "border-top:none;"

        return f"""
        <tr>
            <td style="padding:12px 24px; {border_style}">
                <div style="font-size:15px; color:#111111; line-height:1.5;">
                    {new_badge}{link_html}
                </div>
                {meta_block}
            </td>
        </tr>
        """

    def _build_rank_chip(self, ranks: List[Any]) -> Tuple[str, bool]:
        """将排名列表格式化为徽章文本"""
        normalized: List[int] = []
        for rank in ranks or []:
            try:
                normalized.append(int(rank))
            except (TypeError, ValueError):
                continue

        if not normalized:
            return "", False

        unique_ranks = sorted(set(normalized))
        min_rank = unique_ranks[0]
        max_rank = unique_ranks[-1]

        if min_rank == max_rank:
            label = f"#{min_rank}"
        else:
            label = f"#{min_rank} - #{max_rank}"

        highlight = self.rank_threshold and min_rank <= self.rank_threshold
        return label, bool(highlight)

    def _render_new_section(
        self,
        new_titles: List[Dict[str, Any]],
        total_new_count: int
    ) -> str:
        """渲染新增新闻区域"""
        if not new_titles:
            return ""

        blocks: List[str] = []
        for source_data in new_titles:
            titles = source_data.get("titles", [])
            if not titles:
                continue

            body_rows = []
            for idx, title in enumerate(titles):
                body_rows.append(self._render_news_item(title, is_first=idx == 0))

            blocks.append(self._wrap_card(
                title=html_escape(source_data.get("source_name", "未命名来源")),
                meta_text=html_escape(f"新增 {len(titles)} 条"),
                body_rows="".join(body_rows)
            ))

        if not blocks:
            return ""

        header = """
        <tr>
            <td style="padding:28px 36px 8px 36px; font-size:18px; font-weight:600; color:#111111;">
                📢 最新批次新增
            </td>
        </tr>
        """

        summary_line = ""
        if total_new_count:
            summary_line = f"""
            <tr>
                <td style="padding:0 36px 12px 36px; font-size:13px; color:#6e6e73;">
                    共 {total_new_count} 条新增
                </td>
            </tr>
            """

        return header + summary_line + "".join(blocks)

    def _render_failed_section(self, failed_ids: List[str]) -> str:
        """渲染失败平台告警"""
        if not failed_ids:
            return ""

        unique_failed = sorted({fid for fid in failed_ids if fid})
        if not unique_failed:
            return ""

        failed_text = ", ".join(unique_failed)
        return f"""
        <tr>
            <td style="padding:24px 36px 0 36px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-radius:20px; background-color:#fff4f0; border:1px solid #ffd6cc;">
                    <tr>
                        <td style="padding:18px 20px; font-size:14px; color:#b3261e;">
                            <strong style="display:block; margin-bottom:6px;">⚠️ 以下平台请求失败</strong>
                            <span style="color:#7a2e23;">{html_escape(failed_text)}</span>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """

    def _render_empty_state(self) -> str:
        """当没有统计数据时的占位内容"""
        body_rows = self._render_placeholder_item("当前没有可展示的热点词组，请稍后再试。")
        return self._wrap_card(
            title="暂无数据",
            meta_text="等待新的抓取批次",
            body_rows=body_rows
        )

    def _wrap_card(self, title: str, meta_text: str, body_rows: str) -> str:
        """Apple Mail 风格的卡片容器"""
        return f"""
        <tr>
            <td style="padding:0 36px 16px 36px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate; border-spacing:0; border:1px solid #e3e7ee; border-radius:28px; background-color:#ffffff;">
                    <tr>
                        <td style="padding:20px 24px 10px 24px;">
                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="font-size:18px; font-weight:600; color:#111111;">{title}</td>
                                    <td style="font-size:13px; color:#6e6e73; text-align:right;">{meta_text}</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    {body_rows}
                </table>
            </td>
        </tr>
        """

    def _render_placeholder_item(self, message: str) -> str:
        """无内容时的占位行"""
        return f"""
        <tr>
            <td style="padding:18px 24px;">
                <div style="font-size:14px; color:#6e6e73;">{html_escape(message)}</div>
            </td>
        </tr>
        """
