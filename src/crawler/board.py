"""
NGA 板块爬虫 - 自动获取大时代热门帖子列表
"""
import re
import requests
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
from config import config

logger = logging.getLogger(__name__)


@dataclass
class BoardPost:
    """板块帖子摘要"""
    tid: str
    subject: str
    author: str
    postdate: datetime
    replies: int
    recommend: int
    lastpost: datetime
    lastposter: str
    _hot_score: float = 0.0  # 综合热度评分


class BoardCrawler:
    """NGA 板块爬虫"""

    BASE_URL = "https://bbs.nga.cn/thread.php"

    def __init__(self, cookie: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/x-javascript, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://ngabbs.com/',
        })
        cookie = cookie or config.nga.cookie
        if cookie:
            self.session.headers['Cookie'] = cookie

    def get_posts(
        self,
        fid: str = "706",
        page: int = 1,
        limit: int = 20,
    ) -> List[BoardPost]:
        """
        获取板块帖子列表

        Args:
            fid: 板块ID，706=大时代
            page: 页码
            sort: lastpost=最新回复, postdate=最新发帖
            limit: 返回数量
        """
        params = {"fid": fid, "lite": "js", "page": page}

        try:
            r = self.session.get(self.BASE_URL, params=params, timeout=10)
            if r.status_code != 200:
                logger.warning(f"板块 {fid} 请求失败: HTTP {r.status_code}")
                return []
            r.encoding = 'GBK'
            text = r.text
        except Exception as e:
            logger.warning(f"板块 {fid} 请求失败: {e}")
            return []

        if 'error' in text[:100]:
            logger.warning(f"板块请求返回错误（cookie可能过期）: {text[:200]}")
            return []

        posts = self._parse_text(text)
        return posts[:limit] if limit else posts

    def get_hot_posts(self, fid: str = "706", pages: int = 3) -> List[BoardPost]:
        """
        爬取多页热门帖子，按综合热度排序
        综合热度 = replies * 0.3 + recommend * 2 + time_decay
        """
        all_posts = []
        for page in range(1, pages + 1):
            posts = self.get_posts(fid=fid, page=page, limit=50)
            all_posts.extend(posts)

        # 去重 + 计算热度
        now = datetime.now().timestamp()
        seen = set()
        unique = []
        for p in all_posts:
            if p.tid in seen:
                continue
            seen.add(p.tid)
            age_hours = (now - p.lastpost.timestamp()) / 3600
            time_decay = max(0, 1 - age_hours / 72)
            p._hot_score = p.replies * 0.3 + p.recommend * 2 + time_decay * 10
            unique.append(p)

        unique.sort(key=lambda x: x._hot_score, reverse=True)
        return unique

    def _parse_text(self, text: str) -> List[BoardPost]:
        """解析 lite-js 返回的 JS 文本，直接用正则提取字段"""
        posts = []

        # 提取每条帖子的关键字段
        # NGA lite-js 格式: {"tid":46624153,"fid":706,...,"subject":"标题","author":"作者",...}
        post_blocks = re.findall(
            r'\{"tid":(\d+).*?"subject":"([^"]+)".*?"author":"([^"]+)".*?"postdate":(\d+).*?"lastpost":(\d+).*?"replies":(-?\d+).*?"recommend":(-?\d+).*?"lastposter":"([^"]+)"',
            text
        )

        for block in post_blocks:
            try:
                tid = block[0]
                subject = block[1].replace('&nbsp;', ' ').replace('&amp;', '&')
                author = block[2]
                postdate_ts = int(block[3])
                lastpost_ts = int(block[4])
                replies = max(0, int(block[5]))
                recommend = max(0, int(block[6]))
                lastposter = block[7]

                if not tid or not subject:
                    continue

                posts.append(BoardPost(
                    tid=tid,
                    subject=subject,
                    author=author,
                    postdate=datetime.fromtimestamp(postdate_ts) if postdate_ts else datetime.now(),
                    replies=replies,
                    recommend=recommend,
                    lastpost=datetime.fromtimestamp(lastpost_ts) if lastpost_ts else datetime.now(),
                    lastposter=lastposter,
                ))
            except Exception:
                continue

        return posts
