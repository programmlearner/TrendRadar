"""
YouTube 热门视频信息源

使用 YouTube Data API v3 官方 SDK 获取各地区的热门视频
支持多地区并发请求,按观看数作为热度指标
"""

from typing import List, Dict, Any, Optional
from src.sources.base import BaseSource
from src.models.news import News

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_SDK_AVAILABLE = True
except ImportError:
    YOUTUBE_SDK_AVAILABLE = False
    print("警告: 未安装 google-api-python-client,YouTube 信息源将无法使用")
    print("请运行: pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2")


class YouTubeSource(BaseSource):
    """YouTube 热门视频信息源

    使用 YouTube Data API v3 官方 SDK 的 videos.list 接口获取热门视频
    配置项:
        - api_key: YouTube Data API v3 密钥
        - regions: 监控的地区列表 [{"code": "US", "name": "美国"}]
        - max_results: 每个地区获取的视频数量(1-50)
    """

    # 视频 URL 模板
    VIDEO_URL_TEMPLATE = "https://www.youtube.com/watch?v={video_id}"
    MOBILE_URL_TEMPLATE = "https://m.youtube.com/watch?v={video_id}"

    def __init__(self, config: Dict[str, Any]):
        """初始化 YouTube 信息源

        Args:
            config: 全局配置字典
        """
        super().__init__(config)
        self._youtube_client: Optional[Any] = None

    @property
    def source_id(self) -> str:
        """信息源唯一标识"""
        return "youtube"

    @property
    def source_name(self) -> str:
        """信息源显示名称"""
        return "YouTube 热门"

    def validate_config(self) -> bool:
        """验证配置是否完整

        Returns:
            bool: 配置是否有效
        """
        if not YOUTUBE_SDK_AVAILABLE:
            print(f"警告: {self.source_name} 缺少 google-api-python-client 依赖")
            return False

        source_config = self.get_source_config()

        # 检查 API Key
        api_key = source_config.get("api_key", "").strip()
        if not api_key:
            print(f"警告: {self.source_name} 缺少 API Key 配置")
            return False

        # 检查地区列表
        regions = source_config.get("regions", [])
        if not regions:
            print(f"警告: {self.source_name} 未配置地区列表")
            return False

        # 验证地区配置格式
        for region in regions:
            if not isinstance(region, dict):
                print(f"警告: {self.source_name} 地区配置格式错误,应为字典")
                return False
            if "code" not in region or "name" not in region:
                print(f"警告: {self.source_name} 地区配置缺少 code 或 name 字段")
                return False

        return True

    def fetch_news(self, **kwargs) -> List[News]:
        """获取 YouTube 热门视频列表

        Returns:
            List[News]: 标准化的 News 对象列表
        """
        if not YOUTUBE_SDK_AVAILABLE:
            print(f"警告: {self.source_name} 缺少必要依赖,跳过爬取")
            return []

        # 1. 读取配置
        source_config = self.get_source_config()
        api_key = source_config.get("api_key", "").strip()
        regions = source_config.get("regions", [])
        max_results = source_config.get("max_results", 50)

        # 2. 验证配置
        if not api_key:
            print(f"警告: {self.source_name} 缺少 API Key,跳过爬取")
            return []

        if not regions:
            print(f"警告: {self.source_name} 未配置地区列表,跳过爬取")
            return []

        # 3. 初始化 YouTube 客户端
        try:
            # 使用自定义 HTTP 客户端设置超时
            import httplib2
            http = httplib2.Http(timeout=30)  # 设置 30 秒超时

            self._youtube_client = build('youtube', 'v3', developerKey=api_key, http=http)
        except Exception as e:
            print(f"警告: {self.source_name} 初始化 YouTube 客户端失败: {e}")
            return []

        # 4. 爬取各地区数据
        all_news = []
        for region in regions:
            region_code = region.get("code", "")
            region_name = region.get("name", "")

            if not region_code:
                print(f"警告: 地区配置缺少 code 字段,跳过")
                continue

            print(f"正在获取 {region_name}({region_code}) 的热门视频...")

            # 获取该地区的热门视频
            videos = self._fetch_region_videos(
                region_code=region_code,
                max_results=max_results
            )

            if videos:
                # 转换为 News 对象
                news_list = self._convert_to_news(
                    videos=videos,
                    region_name=region_name
                )
                all_news.extend(news_list)
                print(f"获取 {region_name} 成功,共 {len(news_list)} 条")
            else:
                print(f"获取 {region_name} 失败或无数据")

        print(f"{self.source_name} 共获取 {len(all_news)} 条新闻")
        return all_news

    def _fetch_region_videos(
        self,
        region_code: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """获取指定地区的热门视频

        Args:
            region_code: 地区代码(ISO 3166-1 alpha-2)
            max_results: 获取数量(1-50)

        Returns:
            List[Dict]: 视频数据列表
        """
        try:
            # 调用 YouTube API
            request = self._youtube_client.videos().list(
                part='snippet,statistics',
                chart='mostPopular',
                regionCode=region_code,
                maxResults=min(max_results, 50)
            )
            response = request.execute()

            # 提取视频列表
            items = response.get('items', [])

            if not items:
                print(f"  响应中没有视频数据")
                return []

            return items

        except HttpError as e:
            # 处理 YouTube API HTTP 错误
            error_code = e.resp.status
            error_content = e.content.decode('utf-8') if e.content else ""

            print(f"  ❌ YouTube API 错误:")
            print(f"     HTTP 状态码: {error_code}")

            # 尝试解析错误信息
            try:
                import json
                error_data = json.loads(error_content)
                error_info = error_data.get("error", {})
                error_message = error_info.get("message", "未知错误")
                error_reason = error_info.get("errors", [{}])[0].get("reason", "unknown")

                print(f"     原因: {error_reason}")
                print(f"     详情: {error_message}")

                # 提供针对性的解决建议
                if error_code == 403:
                    print(f"  💡 解决建议:")
                    if "disabled" in error_message.lower() or "not enabled" in error_message.lower():
                        print(f"     1. 访问 https://console.cloud.google.com/apis/library/youtube.googleapis.com")
                        print(f"     2. 确保 YouTube Data API v3 已启用")
                    elif "quota" in error_message.lower():
                        print(f"     1. API 配额已用完,请等待配额重置(每天凌晨 PST 时间)")
                        print(f"     2. 访问 https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas 查看配额")
                    elif "key" in error_message.lower() or "credential" in error_message.lower():
                        print(f"     1. 检查 API Key 是否正确")
                        print(f"     2. 访问 https://console.cloud.google.com/apis/credentials 验证密钥")
                    else:
                        print(f"     1. 检查 API Key 的访问限制(IP 限制、HTTP Referrer 限制)")
                        print(f"     2. 访问 https://console.cloud.google.com/apis/credentials 编辑 API 密钥")
                        print(f"     3. 建议设置为'不限制密钥'(仅用于测试)")
                elif error_code == 400:
                    print(f"  💡 解决建议:")
                    print(f"     1. 检查地区代码是否正确(应为 ISO 3166-1 alpha-2 格式,如 US, JP, KR)")
                    print(f"     2. 检查 maxResults 参数是否在 1-50 范围内")
                elif error_code == 401:
                    print(f"  💡 解决建议:")
                    print(f"     1. API Key 无效或已过期")
                    print(f"     2. 访问 https://console.cloud.google.com/apis/credentials 重新生成密钥")

            except (json.JSONDecodeError, KeyError):
                print(f"     错误内容: {error_content[:200]}")

            return []

        except Exception as e:
            print(f"  请求失败: {e}")
            return []

    def _convert_to_news(
        self,
        videos: List[Dict[str, Any]],
        region_name: str
    ) -> List[News]:
        """将 YouTube 视频数据转换为 News 对象

        Args:
            videos: YouTube API 返回的视频数据列表
            region_name: 地区名称(用于 platform_name)

        Returns:
            List[News]: News 对象列表
        """
        news_list = []

        for idx, video in enumerate(videos, start=1):
            try:
                # 提取视频 ID
                video_id = video.get("id", "")
                if not video_id:
                    continue

                # 提取 snippet 和 statistics
                snippet = video.get("snippet", {})
                statistics = video.get("statistics", {})

                # 提取标题
                title = snippet.get("title", "").strip()
                if not title:
                    continue

                # 提取观看数(字符串转整数)
                view_count_str = statistics.get("viewCount", "0")
                try:
                    view_count = int(view_count_str)
                except (ValueError, TypeError):
                    view_count = 0

                # 提取其他字段
                channel_title = snippet.get("channelTitle", "")
                channel_id = snippet.get("channelId", "")
                published_at = snippet.get("publishedAt", "")
                like_count_str = statistics.get("likeCount", "0")
                comment_count_str = statistics.get("commentCount", "0")
                category_id = snippet.get("categoryId", "")

                # 转换点赞数和评论数
                try:
                    like_count = int(like_count_str)
                except (ValueError, TypeError):
                    like_count = 0

                try:
                    comment_count = int(comment_count_str)
                except (ValueError, TypeError):
                    comment_count = 0

                # 构建 URL
                url = self.VIDEO_URL_TEMPLATE.format(video_id=video_id)
                mobile_url = self.MOBILE_URL_TEMPLATE.format(video_id=video_id)

                # 创建 News 对象
                news = News(
                    title=title,
                    url=url,
                    platform="youtube",  # 统一平台 ID
                    platform_name=f"YouTube {region_name}",  # 平台名称包含地区
                    rank=idx,  # 按 API 返回顺序排名
                    hotness=view_count,  # 观看数作为热度
                    source_id=self.source_id,
                    mobile_url=mobile_url,
                    extra={
                        "video_id": video_id,
                        "channel_title": channel_title,
                        "channel_id": channel_id,
                        "published_at": published_at,
                        "view_count": view_count,
                        "like_count": like_count,
                        "comment_count": comment_count,
                        "category_id": category_id
                    }
                )

                news_list.append(news)

            except Exception as e:
                print(f"  转换视频数据时出错: {e}")
                continue

        return news_list
