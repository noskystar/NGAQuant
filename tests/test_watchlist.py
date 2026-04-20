"""WatchlistManager 单元测试"""
import os
import pytest
from src.watchlist import WatchlistManager, WATCHLIST_PATH


@pytest.fixture(autouse=True)
def clean_watchlist():
    """每个测试前清理 watchlist 文件"""
    # 备份并删除现有文件
    backup = None
    if os.path.exists(WATCHLIST_PATH):
        with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
            backup = f.read()
        os.remove(WATCHLIST_PATH)
    yield
    # 测试后恢复
    if os.path.exists(WATCHLIST_PATH):
        os.remove(WATCHLIST_PATH)
    if backup is not None:
        os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
        with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
            f.write(backup)


class TestWatchlistManager:
    def test_load_empty_when_no_file(self):
        """文件不存在时返回空列表"""
        assert WatchlistManager.load() == []

    def test_load_empty_when_invalid_json(self, tmp_path):
        """文件内容不是合法 JSON 时返回空列表"""
        os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)
        with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
            f.write("not json")
        assert WatchlistManager.load() == []

    def test_load_empty_when_wrong_structure(self):
        """JSON 结构不对时返回空列表"""
        WatchlistManager._ensure_dir()
        with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
            import json
            json.dump({"items": ["123"]}, f)
        assert WatchlistManager.load() == []

    def test_add_and_load(self):
        """添加后正确加载"""
        assert WatchlistManager.add("25914502") is True
        assert WatchlistManager.load() == ["25914502"]

    def test_add_duplicate_returns_false(self):
        """重复添加返回 False"""
        WatchlistManager.add("25914502")
        assert WatchlistManager.add("25914502") is False
        assert WatchlistManager.load() == ["25914502"]

    def test_add_empty_string_returns_false(self):
        """添加空字符串返回 False"""
        assert WatchlistManager.add("") is False
        assert WatchlistManager.add("  ") is False

    def test_add_strips_whitespace(self):
        """添加时去除前后空格"""
        WatchlistManager.add("  25914502  ")
        assert WatchlistManager.load() == ["25914502"]

    def test_add_converts_to_string(self):
        """数字 tid 自动转字符串"""
        WatchlistManager.add(25914502)
        assert WatchlistManager.load() == ["25914502"]

    def test_remove_existing(self):
        """删除存在的 ID"""
        WatchlistManager.add("25914502")
        assert WatchlistManager.remove("25914502") is True
        assert WatchlistManager.load() == []

    def test_remove_nonexistent_returns_false(self):
        """删除不存在的 ID 返回 False"""
        assert WatchlistManager.remove("99999999") is False

    def test_remove_strips_whitespace(self):
        """删除时去除前后空格"""
        WatchlistManager.add("25914502")
        assert WatchlistManager.remove("  25914502  ") is True

    def test_persistence_across_instances(self):
        """数据持久化到文件"""
        WatchlistManager.add("111")
        WatchlistManager.add("222")
        # 模拟新实例（直接重新加载）
        loaded = WatchlistManager.load()
        assert loaded == ["111", "222"]
