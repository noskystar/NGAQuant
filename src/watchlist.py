"""关注帖子管理 - 基于本地 JSON 文件持久化"""
import json
import os
from typing import List


# 使用项目根目录下的 data/ 文件夹
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST_PATH = os.path.join(_PROJECT_ROOT, "data", "watchlist.json")


class WatchlistManager:
    """管理用户关注的帖子 ID 列表"""

    @staticmethod
    def _ensure_dir():
        """确保数据目录存在"""
        os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)

    @staticmethod
    def load() -> List[str]:
        """加载关注列表，文件不存在或损坏时返回空列表"""
        if not os.path.exists(WATCHLIST_PATH):
            return []
        try:
            with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("ids"), list):
                    return [str(tid) for tid in data["ids"]]
                return []
        except (json.JSONDecodeError, IOError, KeyError, TypeError):
            return []

    @staticmethod
    def save(ids: List[str]):
        """保存关注列表到 JSON"""
        WatchlistManager._ensure_dir()
        with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
            json.dump({"ids": ids}, f, ensure_ascii=False, indent=2)

    @staticmethod
    def add(tid: str) -> bool:
        """添加帖子 ID，去重。返回 True 表示成功添加"""
        ids = WatchlistManager.load()
        normalized = str(tid).strip()
        if normalized and normalized not in ids:
            ids.append(normalized)
            WatchlistManager.save(ids)
            return True
        return False

    @staticmethod
    def remove(tid: str) -> bool:
        """删除帖子 ID。返回 True 表示成功删除"""
        ids = WatchlistManager.load()
        normalized = str(tid).strip()
        if normalized in ids:
            ids.remove(normalized)
            WatchlistManager.save(ids)
            return True
        return False
