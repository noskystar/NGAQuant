"""
NGA论坛爬虫模块 - 用于抓取大时代板块帖子
"""
import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.utils.logger import logger
from src.config import config


@dataclass
class NGAPost:
    """NGA帖子数据模型"""
    post_id: str
    author: str
    author_uid: str
    content: str
    timestamp: datetime
    floor: int
    is_main_post: bool = False

class NGACrawler:
    """NGA爬虫客户端"""
    
    BASE_URL = "https://bbs.nga.cn"
    
    def __init__(self, cookie: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if cookie:
            self.session.headers['Cookie'] = cookie
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.RequestException, ConnectionError)),
        reraise=True
    )
    def _fetch_page(self, url: str) -> requests.Response:
        """获取页面内容（带重试）"""
        response = self.session.get(url, timeout=config.nga.timeout)
        response.encoding = 'utf-8'
        return response
    
    def get_thread(self, tid: str, page: int = 1) -> List[NGAPost]:
        """
        获取帖子内容
        
        Args:
            tid: 帖子ID
            page: 页码
            
        Returns:
            帖子列表
        """
        url = f"{self.BASE_URL}/read.php?tid={tid}&page={page}"
        
        try:
            response = self._fetch_page(url)
            
            if response.status_code != 200:
                logger.warning(f"请求失败: {response.status_code} for tid={tid}, page={page}")
                return []
            
            # 检查是否需要登录
            if "登陆" in response.text or "登录" in response.text or "权限不足" in response.text:
                logger.warning(f"帖子 {tid} 可能需要登录才能访问")
            
            return self._parse_posts(response.text, tid)
            
        except Exception as e:
            logger.error(f"爬取失败 tid={tid}, page={page}: {e}")
            return []
    
    def _parse_posts(self, html: str, tid: str) -> List[NGAPost]:
        """解析帖子HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        posts = []
        
        # NGA帖子选择器 - 尝试多种可能的选择器
        post_elements = soup.select('.postbox, .forumbox .c0, .plc, .postcontent')
        
        # 如果没找到，尝试更通用的选择
        if not post_elements:
            # 尝试查找包含用户内容的div
            post_elements = soup.find_all(['div', 'td'], class_=lambda x: x and ('post' in x.lower() or 'content' in x.lower()))
        
        logger.debug(f"找到 {len(post_elements)} 个帖子元素")
        
        for idx, element in enumerate(post_elements):
            try:
                # 提取作者 - 尝试多种选择器
                author_elem = (
                    element.select_one('.author, .postauthor, .auth') or
                    element.find_previous(['div', 'td'], class_=lambda x: x and 'author' in str(x).lower())
                )
                author = author_elem.get_text(strip=True) if author_elem else f"用户{idx}"
                
                # 提取内容 - 尝试多种选择器
                content_elem = (
                    element.select_one('.postcontent, .forumbox_main, .txtstyle, .message') or
                    element
                )
                content = content_elem.get_text('\n', strip=True) if content_elem else ""
                
                # 清理内容
                content = re.sub(r'\n+', '\n', content)  # 合并多余换行
                content = content.strip()
                
                # 提取时间 - 尝试多种选择器
                time_elem = (
                    element.select_one('.postdate, .author .silver, .time') or
                    element.find_previous(string=re.compile(r'\d{4}-\d{2}-\d{2}'))
                )
                
                timestamp = datetime.now()
                if time_elem:
                    if hasattr(time_elem, 'text'):
                        timestamp = self._parse_time(time_elem.text)
                    else:
                        timestamp = self._parse_time(str(time_elem))
                
                # 提取UID
                uid_match = re.search(r'uid=(\d+)', str(element))
                author_uid = uid_match.group(1) if uid_match else "0"
                
                post = NGAPost(
                    post_id=f"{tid}_{idx}",
                    author=author,
                    author_uid=author_uid,
                    content=content,
                    timestamp=timestamp,
                    floor=idx + 1,
                    is_main_post=(idx == 0)
                )
                posts.append(post)
                
            except Exception as e:
                logger.warning(f"解析第 {idx} 个帖子失败: {e}")
                continue
        
        return posts
    
    def _parse_time(self, time_str: str) -> datetime:
        """解析时间字符串"""
        # NGA时间格式: 2024-01-15 14:30:00
        try:
            return datetime.strptime(time_str.strip(), '%Y-%m-%d %H:%M:%S')
        except:
            return datetime.now()
    
    def get_total_pages(self, tid: str) -> int:
        """获取帖子总页数"""
        url = f"{self.BASE_URL}/read.php?tid={tid}"
        
        try:
            response = self._fetch_page(url)
            
            # 查找页数信息
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 尝试多种选择器
            page_info = soup.select_one('.pager, .pagination, .page')
            
            if page_info:
                # 方法1: 从分页链接中提取最大页码
                page_links = page_info.find_all('a')
                max_page = 1
                for link in page_links:
                    text = link.get_text(strip=True)
                    if text.isdigit():
                        max_page = max(max_page, int(text))
                
                if max_page > 1:
                    return max_page
                
                # 方法2: 正则匹配
                page_match = re.search(r'(\d+)</a>\s*<a[^>]*>下一页', str(page_info))
                if page_match:
                    return int(page_match.group(1))
            
            # 方法3: 从帖子数量估算
            posts = self._parse_posts(response.text, tid)
            if len(posts) >= 20:  # 每页通常20条
                # 可能有更多页，但先返回1，让调用方决定
                pass
            
            return 1
            
        except Exception as e:
            logger.error(f"获取页数失败 tid={tid}: {e}")
            return 1
    
    def get_full_thread(self, tid: str, max_pages: Optional[int] = None) -> List[NGAPost]:
        """
        获取完整帖子（所有页）
        
        Args:
            tid: 帖子ID
            max_pages: 最大页数限制
            
        Returns:
            所有帖子列表
        """
        total_pages = self.get_total_pages(tid)
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        all_posts = []
        
        print(f"帖子共 {total_pages} 页，开始爬取...")
        
        for page in range(1, total_pages + 1):
            logger.info(f"爬取第 {page}/{total_pages} 页...")
            posts = self.get_thread(tid, page)
            all_posts.extend(posts)
            
            # 礼貌延迟，避免请求过快
            if page < total_pages:
                delay = config.nga.request_delay
                logger.debug(f"等待 {delay} 秒...")
                time.sleep(delay)
        
        print(f"共爬取 {len(all_posts)} 条回复")
        return all_posts

# 测试代码
if __name__ == "__main__":
    # 测试爬虫
    crawler = NGACrawler()
    
    # 测试帖子ID（替换为实际ID）
    test_tid = "12345678"
    
    posts = crawler.get_thread(test_tid, page=1)
    
    for post in posts[:3]:
        print(f"\n楼层: {post.floor}")
        print(f"作者: {post.author}")
        print(f"内容: {post.content[:100]}...")
        print("-" * 50)
