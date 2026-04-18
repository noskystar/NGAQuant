# 单元测试 - 爬虫模块
import pytest
from src.crawler.nga_client import NGACrawler, NGAPost
from datetime import datetime

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
