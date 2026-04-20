"""
NGA论坛爬虫模块 - 用于抓取大时代板块帖子
"""
import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
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
        response.encoding = 'GB18030'
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
        
        # 只选择 .postbox（每个帖子是一个 table.postbox）
        post_elements = soup.select('table.postbox')
        
        # 如果没找到，尝试备选选择器
        if not post_elements:
            post_elements = soup.select('.forumbox')
        
        logger.debug(f"找到 {len(post_elements)} 个帖子元素")
        
        for element in post_elements:
            try:
                # 从 row id 提取实际楼层号
                row_elem = element.select_one('tr.postrow')
                row_id = row_elem.get('id', '') if row_elem else ''
                floor_match = re.search(r'row(\d+)$', row_id)
                floor = int(floor_match.group(1)) + 1 if floor_match else 0
                
                # 提取作者 - NGA用户名由JS渲染，优先取uid作为标识
                author_elem = element.select_one('a.author')
                if author_elem:
                    author = author_elem.get('href', '')
                    uid_match = re.search(r'uid=(\d+)', author)
                    author = f"uid-{uid_match.group(1)}" if uid_match else author_elem.get_text(strip=True) or f"用户{floor}"
                else:
                    author = f"用户{floor}"
                
                # 提取内容 - 每个 postbox 里的 .c2 单元格
                content_elem = element.select_one('.c2')
                if not content_elem:
                    content_elem = element.select_one('.postcontent, .txtstyle')
                content = content_elem.get_text('\n', strip=True) if content_elem else ""
                
                # 清理内容
                content = re.sub(r'\[[^\]]+\]', '', content)  # 去除 [s:ac:xxx] 等NGA标签
                content = re.sub(r'\[url\].*?\[/url\]', '', content, flags=re.DOTALL)  # 去除URL标签
                content = re.sub(r'\[quote\].*?\[/quote\]', '', content, flags=re.DOTALL)  # 去除引用
                content = re.sub(r'\[tid=.*?\[/tid\]', '', content)  # 去除引用楼层标签
                content = re.sub(r'\[b\].*?\[/b\]', '', content)  # 去除加粗标签
                content = re.sub(r'\n+', '\n', content)  # 合并多余换行
                content = content.strip()
                
                # 去除开头的时间戳（如 "2026-01-12 09:05\n"）
                content = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s*', '', content)
                
                # 跳过太短的内容（可能是引用楼层或空楼层）
                if len(content) < 3:
                    continue
                
                # 提取时间 - 从 .c2 内容的开头提取时间戳
                timestamp = datetime.now()
                if content_elem:
                    raw_text = content_elem.get_text()
                    time_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', raw_text)
                    if time_match:
                        timestamp = self._parse_time(time_match.group(1))
                
                # 提取UID - 从 a.author 的 href 中提取
                author_uid = "0"
                if author_elem:
                    href = author_elem.get('href', '')
                    uid_m = re.search(r'uid=(\d+)', href)
                    if uid_m:
                        author_uid = uid_m.group(1)
                        author = f"uid-{author_uid}"
                
                post = NGAPost(
                    post_id=f"{tid}_{floor}",
                    author=author,
                    author_uid=author_uid,
                    content=content,
                    timestamp=timestamp,
                    floor=floor,
                    is_main_post=(floor == 1)
                )
                posts.append(post)
                
            except Exception as e:
                logger.warning(f"解析第 {floor} 个帖子失败: {e}")
                continue
        
        return posts
    
    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串。解析失败返回 None（避免 datetime.now() 导致 max_hours 过滤失效）"""
        # NGA时间格式: 2024-01-15 14:30:00
        try:
            return datetime.strptime(time_str.strip(), '%Y-%m-%d %H:%M:%S')
        except:
            return None
    
    def get_total_pages(self, tid: str) -> int:
        """获取帖子总页数"""
        url = f"{self.BASE_URL}/read.php?tid={tid}"

        try:
            response = self._fetch_page(url)
            html = response.text

            # 方法1: 从 JavaScript __PAGE 变量中提取（如 __PAGE = {0:..., 1:4031, 2:1, 3:20}）
            page_match = re.search(r'__PAGE\s*=\s*\{[^}]*1:(\d+)', html)
            if page_match:
                total = int(page_match.group(1))
                if total > 1:
                    return total

            # 方法2: 从URL中直接提取最大页码
            pages_in_url = re.findall(r'[?&]page=(\d+)', html)
            if pages_in_url:
                return max(int(p) for p in pages_in_url)

            # 方法3: 从分页文本中找 "下一页(N)"
            next_pages = re.findall(r'下一页\((\d+)\)', html)
            if next_pages:
                return max(int(p) for p in next_pages)

            return 1

        except Exception as e:
            logger.error(f"获取页数失败 tid={tid}: {e}")
            return 1
    def get_full_thread(self, tid: str, max_pages: Optional[int] = None, max_hours: int = 0) -> List[NGAPost]:
        """
        获取完整帖子（从最新页开始倒序爬取）

        Args:
            tid: 帖子ID
            max_pages: 最大页数限制（从最后一页往前数）
            max_hours: 只分析近 max_hours 内的回复，0 表示不过滤

        Returns:
            所有帖子列表（按楼层号升序排列，越新的在后面）
        """
        total_pages = self.get_total_pages(tid)

        # 计算爬取范围：从最后一页往前取 max_pages 页
        start_page = total_pages
        end_page = 1
        if max_pages and max_pages > 0:
            end_page = max(1, total_pages - max_pages + 1)

        all_posts = []
        cutoff_time = None
        if max_hours > 0:
            from datetime import timezone
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_hours)

        print(f"帖子共 {total_pages} 页，从第 {start_page} 页倒序爬取至第 {end_page} 页...")

        for page in range(start_page, end_page - 1, -1):
            logger.info(f"爬取第 {page}/{total_pages} 页...")
            posts = self.get_thread(tid, page)

            all_posts.extend(posts)

            # Early-break: 用该页最新帖子（楼层号最大）判断整页是否已超时
            if cutoff_time and posts:
                latest_post = max(posts, key=lambda p: p.floor)
                if latest_post.timestamp is not None and latest_post.timestamp.timestamp() < cutoff_time.timestamp():
                    print(f"第 {page} 页最新帖子已早于 {max_hours}h，停止爬取")
                    break

            if page > end_page:
                delay = config.nga.request_delay
                logger.debug(f"等待 {delay} 秒...")
                time.sleep(delay)

        # 按时间过滤
        if max_hours > 0:
            all_posts = filter_posts_by_hours(all_posts, max_hours)

        print(f"共爬取 {len(all_posts)} 条回复（已过滤）")
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


def filter_posts_by_hours(posts: List[NGAPost], max_hours: int) -> List[NGAPost]:
    """
    按时间过滤帖子，只保留近 max_hours 内的回复
    
    Args:
        posts: 帖子列表
        max_hours: 最大小时数，0 表示不过滤
        
    Returns:
        过滤后的帖子列表
    """
    if max_hours <= 0:
        return posts

    from datetime import timezone
    now = datetime.now(timezone.utc)
    cutoff = now.timestamp() - max_hours * 3600
    
    filtered = []
    for post in posts:
        if post.timestamp is not None and post.timestamp.timestamp() >= cutoff:
            filtered.append(post)
    
    return filtered
