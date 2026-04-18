# NGA大时代爬虫客户端
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
            response = self.session.get(url, timeout=30)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"请求失败: {response.status_code}")
                return []
            
            return self._parse_posts(response.text, tid)
            
        except Exception as e:
            print(f"爬取失败: {e}")
            return []
    
    def _parse_posts(self, html: str, tid: str) -> List[NGAPost]:
        """解析帖子HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        posts = []
        
        # NGA帖子选择器
        post_elements = soup.select('.postbox, .forumbox, .c0')
        
        for idx, element in enumerate(post_elements):
            try:
                # 提取作者
                author_elem = element.select_one('.author, .postauthor')
                author = author_elem.text.strip() if author_elem else "未知"
                
                # 提取内容
                content_elem = element.select_one('.postcontent, .forumbox_main, .txtstyle')
                content = content_elem.get_text('\n', strip=True) if content_elem else ""
                
                # 提取时间
                time_elem = element.select_one('.postdate, .author .silver')
                timestamp = self._parse_time(time_elem.text) if time_elem else datetime.now()
                
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
                print(f"解析帖子失败: {e}")
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
            response = self.session.get(url, timeout=30)
            response.encoding = 'utf-8'
            
            # 查找页数信息
            soup = BeautifulSoup(response.text, 'html.parser')
            page_info = soup.select_one('.pager, .pagination')
            
            if page_info:
                # 提取最大页码
                page_match = re.search(r'(\d+)</a>\s*<a[^>]*>下一页', str(page_info))
                if page_match:
                    return int(page_match.group(1))
            
            return 1
            
        except Exception as e:
            print(f"获取页数失败: {e}")
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
            print(f"爬取第 {page}/{total_pages} 页...")
            posts = self.get_thread(tid, page)
            all_posts.extend(posts)
            
            #  polite delay
            if page < total_pages:
                time.sleep(2)
        
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
