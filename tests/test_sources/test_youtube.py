# coding=utf-8
"""YouTube Source 单元测试"""

import pytest
from unittest.mock import Mock, patch
from src.sources.youtube import YouTubeSource
from src.models.news import News


class TestYouTubeSource:
    """YouTube Source 测试类"""

    def test_source_id(self):
        """测试 source_id 属性"""
        config = {"SOURCES": {"enabled": ["youtube"]}}
        source = YouTubeSource(config)
        assert source.source_id == "youtube"

    def test_source_name(self):
        """测试 source_name 属性"""
        config = {"SOURCES": {"enabled": ["youtube"]}}
        source = YouTubeSource(config)
        assert source.source_name == "YouTube 热门"

    def test_is_enabled_when_in_enabled_list(self):
        """测试当在启用列表中时 is_enabled 返回 True"""
        config = {"SOURCES": {"enabled": ["youtube"]}}
        source = YouTubeSource(config)
        assert source.is_enabled is True

    def test_is_enabled_when_not_in_enabled_list(self):
        """测试当不在启用列表中时 is_enabled 返回 False"""
        config = {"SOURCES": {"enabled": ["newsnow"]}}
        source = YouTubeSource(config)
        assert source.is_enabled is False

    def test_validate_config_without_api_key(self):
        """测试没有 API Key 时配置验证失败"""
        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "regions": [
                        {"code": "US", "name": "美国"}
                    ]
                }
            }
        }
        source = YouTubeSource(config)
        assert source.validate_config() is False

    def test_validate_config_without_regions(self):
        """测试没有地区列表时配置验证失败"""
        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "api_key": "test_key"
                }
            }
        }
        source = YouTubeSource(config)
        assert source.validate_config() is False

    def test_validate_config_with_invalid_region_format(self):
        """测试地区配置格式错误时验证失败"""
        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "api_key": "test_key",
                    "regions": ["US", "JP"]  # 错误格式（应该是字典列表）
                }
            }
        }
        source = YouTubeSource(config)
        assert source.validate_config() is False

    def test_validate_config_with_missing_region_fields(self):
        """测试地区配置缺少字段时验证失败"""
        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "api_key": "test_key",
                    "regions": [
                        {"code": "US"}  # 缺少 name 字段
                    ]
                }
            }
        }
        source = YouTubeSource(config)
        assert source.validate_config() is False

    def test_validate_config_success(self):
        """测试配置验证成功"""
        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "api_key": "test_key",
                    "regions": [
                        {"code": "US", "name": "美国"}
                    ]
                }
            }
        }
        source = YouTubeSource(config)
        assert source.validate_config() is True

    def test_fetch_news_without_api_key(self):
        """测试没有 API Key 时返回空列表"""
        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "regions": [
                        {"code": "US", "name": "美国"}
                    ]
                }
            }
        }
        source = YouTubeSource(config)
        news_list = source.fetch_news()
        assert isinstance(news_list, list)
        assert len(news_list) == 0

    def test_fetch_news_without_regions(self):
        """测试没有地区列表时返回空列表"""
        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "api_key": "test_key"
                }
            }
        }
        source = YouTubeSource(config)
        news_list = source.fetch_news()
        assert isinstance(news_list, list)
        assert len(news_list) == 0

    @patch('src.sources.youtube.HTTPClient')
    def test_fetch_news_api_request_failure(self, mock_http_client_class):
        """测试 API 请求失败时处理"""
        # Mock HTTP 客户端
        mock_http_client = Mock()
        mock_http_client.get.return_value = ("", False, "Network error")
        mock_http_client_class.return_value = mock_http_client

        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "api_key": "test_key",
                    "regions": [
                        {"code": "US", "name": "美国"}
                    ],
                    "max_results": 10
                }
            }
        }

        source = YouTubeSource(config)
        news_list = source.fetch_news()

        assert isinstance(news_list, list)
        assert len(news_list) == 0
        mock_http_client.close.assert_called_once()

    @patch('src.sources.youtube.HTTPClient')
    def test_fetch_news_invalid_json_response(self, mock_http_client_class):
        """测试返回无效 JSON 时处理"""
        # Mock HTTP 客户端
        mock_http_client = Mock()
        mock_http_client.get.return_value = ("invalid json", True, None)
        mock_http_client_class.return_value = mock_http_client

        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "api_key": "test_key",
                    "regions": [
                        {"code": "US", "name": "美国"}
                    ],
                    "max_results": 10
                }
            }
        }

        source = YouTubeSource(config)
        news_list = source.fetch_news()

        assert isinstance(news_list, list)
        assert len(news_list) == 0
        mock_http_client.close.assert_called_once()

    @patch('src.sources.youtube.HTTPClient')
    def test_fetch_news_success(self, mock_http_client_class):
        """测试成功获取视频数据"""
        # Mock API 响应数据
        mock_response = {
            "items": [
                {
                    "id": "video_id_1",
                    "snippet": {
                        "title": "测试视频 1",
                        "channelTitle": "测试频道",
                        "channelId": "channel_id_1",
                        "publishedAt": "2025-01-15T10:00:00Z",
                        "categoryId": "10"
                    },
                    "statistics": {
                        "viewCount": "1234567",
                        "likeCount": "12345",
                        "commentCount": "567"
                    }
                },
                {
                    "id": "video_id_2",
                    "snippet": {
                        "title": "测试视频 2",
                        "channelTitle": "测试频道 2",
                        "channelId": "channel_id_2",
                        "publishedAt": "2025-01-15T11:00:00Z",
                        "categoryId": "20"
                    },
                    "statistics": {
                        "viewCount": "987654",
                        "likeCount": "9876",
                        "commentCount": "432"
                    }
                }
            ]
        }

        import json
        mock_json_response = json.dumps(mock_response)

        # Mock HTTP 客户端
        mock_http_client = Mock()
        mock_http_client.get.return_value = (mock_json_response, True, None)
        mock_http_client_class.return_value = mock_http_client

        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "api_key": "test_key",
                    "regions": [
                        {"code": "US", "name": "美国"}
                    ],
                    "max_results": 10
                }
            }
        }

        source = YouTubeSource(config)
        news_list = source.fetch_news()

        # 验证结果
        assert isinstance(news_list, list)
        assert len(news_list) == 2

        # 验证第一条新闻
        news1 = news_list[0]
        assert isinstance(news1, News)
        assert news1.title == "测试视频 1"
        assert news1.url == "https://www.youtube.com/watch?v=video_id_1"
        assert news1.platform == "youtube"
        assert news1.platform_name == "YouTube 美国"
        assert news1.rank == 1
        assert news1.hotness == 1234567
        assert news1.source_id == "youtube"
        assert news1.mobile_url == "https://m.youtube.com/watch?v=video_id_1"
        assert news1.extra["video_id"] == "video_id_1"
        assert news1.extra["channel_title"] == "测试频道"
        assert news1.extra["view_count"] == 1234567
        assert news1.extra["like_count"] == 12345
        assert news1.extra["comment_count"] == 567

        # 验证第二条新闻
        news2 = news_list[1]
        assert news2.title == "测试视频 2"
        assert news2.rank == 2
        assert news2.hotness == 987654

        # 验证 HTTP 客户端调用
        mock_http_client.get.assert_called_once()
        mock_http_client.close.assert_called_once()

    @patch('src.sources.youtube.HTTPClient')
    def test_fetch_news_multiple_regions(self, mock_http_client_class):
        """测试多个地区的数据获取"""
        # Mock API 响应数据
        mock_response = {
            "items": [
                {
                    "id": "video_id_1",
                    "snippet": {
                        "title": "测试视频",
                        "channelTitle": "测试频道",
                        "channelId": "channel_id",
                        "publishedAt": "2025-01-15T10:00:00Z",
                        "categoryId": "10"
                    },
                    "statistics": {
                        "viewCount": "1000000",
                        "likeCount": "10000",
                        "commentCount": "500"
                    }
                }
            ]
        }

        import json
        mock_json_response = json.dumps(mock_response)

        # Mock HTTP 客户端（每次调用返回相同的数据）
        mock_http_client = Mock()
        mock_http_client.get.return_value = (mock_json_response, True, None)
        mock_http_client_class.return_value = mock_http_client

        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "api_key": "test_key",
                    "regions": [
                        {"code": "US", "name": "美国"},
                        {"code": "JP", "name": "日本"}
                    ],
                    "max_results": 10
                }
            }
        }

        source = YouTubeSource(config)
        news_list = source.fetch_news()

        # 验证结果（2 个地区 × 1 条视频 = 2 条新闻）
        assert isinstance(news_list, list)
        assert len(news_list) == 2

        # 验证平台名称不同
        assert news_list[0].platform_name == "YouTube 美国"
        assert news_list[1].platform_name == "YouTube 日本"

        # 验证 HTTP 客户端被调用了 2 次
        assert mock_http_client.get.call_count == 2
        mock_http_client.close.assert_called_once()

    @patch('src.sources.youtube.HTTPClient')
    def test_fetch_news_with_proxy(self, mock_http_client_class):
        """测试使用代理时的配置"""
        # Mock HTTP 客户端
        mock_http_client = Mock()
        mock_http_client.get.return_value = ('{"items": []}', True, None)
        mock_http_client_class.return_value = mock_http_client

        config = {
            "USE_PROXY": True,
            "DEFAULT_PROXY": "http://127.0.0.1:10086",
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {
                    "api_key": "test_key",
                    "regions": [
                        {"code": "US", "name": "美国"}
                    ]
                }
            }
        }

        source = YouTubeSource(config)
        source.fetch_news()

        # 验证 HTTPClient 使用代理初始化
        mock_http_client_class.assert_called_once_with(
            proxy_url="http://127.0.0.1:10086",
            timeout=10
        )

    def test_convert_to_news_with_missing_fields(self):
        """测试转换时缺少字段的处理"""
        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {}
            }
        }
        source = YouTubeSource(config)

        # 测试缺少 id
        videos = [{"snippet": {"title": "测试"}, "statistics": {}}]
        news_list = source._convert_to_news(videos, "美国")
        assert len(news_list) == 0

        # 测试缺少 title
        videos = [{"id": "video_id", "snippet": {}, "statistics": {}}]
        news_list = source._convert_to_news(videos, "美国")
        assert len(news_list) == 0

    def test_convert_to_news_with_invalid_view_count(self):
        """测试观看数无效时的处理"""
        config = {
            "SOURCES": {
                "enabled": ["youtube"],
                "youtube": {}
            }
        }
        source = YouTubeSource(config)

        videos = [
            {
                "id": "video_id",
                "snippet": {"title": "测试视频"},
                "statistics": {"viewCount": "invalid"}  # 无效的观看数
            }
        ]

        news_list = source._convert_to_news(videos, "美国")
        assert len(news_list) == 1
        assert news_list[0].hotness == 0  # 应该使用默认值 0
