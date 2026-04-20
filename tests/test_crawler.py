# 单元测试 - 爬虫模块
import pytest
from src.crawler.nga_client import NGACrawler, NGAPost, filter_posts_by_hours
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

class TestNGACrawler:
    """测试NGA爬虫"""

    @pytest.fixture
    def crawler(self):
        return NGACrawler()

    def test_get_thread(self, crawler):
        """测试获取帖子"""
        # 使用模拟测试
        posts = crawler.get_thread("12345678", page=1)
        assert isinstance(posts, list)

    def test_parse_time(self, crawler):
        """测试时间解析"""
        result = crawler._parse_time("2024-01-15 14:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_post_model(self):
        """测试帖子数据模型"""
        post = NGAPost(
            post_id="123_1",
            author="test_user",
            author_uid="12345",
            content="测试内容",
            timestamp=datetime.now(),
            floor=1,
            is_main_post=True
        )
        assert post.author == "test_user"
        assert post.is_main_post == True


class TestGetFullThreadReverse:
    """测试 get_full_thread 倒序爬取逻辑"""

    def _make_post(self, floor: int, timestamp: datetime = None) -> NGAPost:
        return NGAPost(
            post_id=f"123_{floor}",
            author="test",
            author_uid="1",
            content=f"content {floor}",
            timestamp=timestamp or datetime.now(timezone.utc),
            floor=floor,
            is_main_post=(floor == 1),
        )

    @patch.object(NGACrawler, 'get_thread')
    @patch.object(NGACrawler, 'get_total_pages')
    def test_max_pages_takes_last_n_pages(self, mock_total, mock_get_thread):
        """max_pages=2 时只爬最后 2 页"""
        mock_total.return_value = 10
        # 模拟每页返回 1 条帖子
        mock_get_thread.side_effect = lambda tid, page: [self._make_post(page * 10)]

        crawler = NGACrawler()
        posts = crawler.get_full_thread("123", max_pages=2)

        # 应该只调用了 page=10 和 page=9
        called_pages = [call[0][1] for call in mock_get_thread.call_args_list]
        assert called_pages == [10, 9]

    @patch.object(NGACrawler, 'get_thread')
    @patch.object(NGACrawler, 'get_total_pages')
    def test_max_pages_larger_than_total(self, mock_total, mock_get_thread):
        """max_pages 大于总页数时爬取全部"""
        mock_total.return_value = 3
        mock_get_thread.side_effect = lambda tid, page: [self._make_post(page)]

        crawler = NGACrawler()
        posts = crawler.get_full_thread("123", max_pages=10)

        called_pages = [call[0][1] for call in mock_get_thread.call_args_list]
        assert called_pages == [3, 2, 1]

    @patch.object(NGACrawler, 'get_thread')
    @patch.object(NGACrawler, 'get_total_pages')
    def test_max_pages_none_crawls_all(self, mock_total, mock_get_thread):
        """max_pages=None 时爬取全部"""
        mock_total.return_value = 3
        mock_get_thread.side_effect = lambda tid, page: [self._make_post(page)]

        crawler = NGACrawler()
        posts = crawler.get_full_thread("123", max_pages=None)

        called_pages = [call[0][1] for call in mock_get_thread.call_args_list]
        assert called_pages == [3, 2, 1]

    @patch.object(NGACrawler, 'get_thread')
    @patch.object(NGACrawler, 'get_total_pages')
    def test_early_break_on_old_page(self, mock_total, mock_get_thread):
        """当整页最新帖子都超时，提前停止"""
        mock_total.return_value = 5
        old_time = datetime.now(timezone.utc) - timedelta(hours=100)
        new_time = datetime.now(timezone.utc) - timedelta(hours=1)

        def side_effect(tid, page):
            # page 5 全部新，page 4 全部旧
            if page == 5:
                return [self._make_post(50, new_time), self._make_post(49, new_time)]
            else:
                return [self._make_post(page * 10, old_time)]

        mock_get_thread.side_effect = side_effect

        crawler = NGACrawler()
        posts = crawler.get_full_thread("123", max_pages=None, max_hours=24)

        called_pages = [call[0][1] for call in mock_get_thread.call_args_list]
        # 爬完 page 5，发现 page 4 最新帖子也超时，break
        assert called_pages == [5, 4]


class TestFilterPostsByHours:
    """测试时间过滤函数"""

    def test_none_timestamp_kept(self):
        """None 时间戳的帖子应保留（不过滤）"""
        now = datetime.now(timezone.utc)
        posts = [
            NGAPost("1", "a", "1", "x", None, 1, False),
            NGAPost("2", "a", "1", "x", now, 2, False),
        ]
        result = filter_posts_by_hours(posts, 1)
        assert len(result) == 1
        assert result[0].floor == 2

    def test_all_posts_within_range(self):
        """全部在时间范围内时原样返回"""
        now = datetime.now(timezone.utc)
        posts = [
            NGAPost("1", "a", "1", "x", now - timedelta(minutes=30), 1, False),
            NGAPost("2", "a", "1", "x", now - timedelta(minutes=10), 2, False),
        ]
        result = filter_posts_by_hours(posts, 1)
        assert len(result) == 2

    def test_mixed_posts(self):
        """混有新旧帖子时只保留新的"""
        now = datetime.now(timezone.utc)
        posts = [
            NGAPost("1", "a", "1", "x", now - timedelta(hours=3), 1, False),
            NGAPost("2", "a", "1", "x", now - timedelta(minutes=10), 2, False),
            NGAPost("3", "a", "1", "x", None, 3, False),
        ]
        result = filter_posts_by_hours(posts, 1)
        assert len(result) == 1
        assert result[0].floor == 2
