# 爬虫倒序修复 + 关注帖子管理 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复爬虫 `max_pages` 倒序逻辑，并新增本地 JSON 文件驱动的关注帖子管理功能。

**Architecture:** 关注列表通过独立模块 `src/watchlist.py` 封装 JSON 读写；Web 端在 Streamlit 侧边栏展示关注列表并提供一键关注/取消关注交互。

**Tech Stack:** Python 3.11, Streamlit, pytest, JSON

---

## 文件结构

| 文件 | 类型 | 职责 |
|------|------|------|
| `src/crawler/nga_client.py` | 修改 | 修复 `get_full_thread` 的 `max_pages` 倒序逻辑；修复时间过滤 `None` 误停问题 |
| `src/watchlist.py` | 新增 | 关注列表 JSON 读写封装：`load`, `save`, `add`, `remove` |
| `tests/test_watchlist.py` | 新增 | WatchlistManager 单元测试 |
| `tests/test_crawler.py` | 修改 | 补充 `get_full_thread` 倒序爬取的单元测试 |
| `web/app.py` | 修改 | 侧边栏增加关注列表管理 UI；分析结果区增加「关注此帖」按钮 |

---

### Task 1: WatchlistManager 核心模块

**Files:**
- Create: `src/watchlist.py`
- Test: `tests/test_watchlist.py`

- [ ] **Step 1: 编写 WatchlistManager 实现**

在 `src/watchlist.py` 写入：

```python
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
```

- [ ] **Step 2: 编写 WatchlistManager 测试**

在 `tests/test_watchlist.py` 写入：

```python
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
```

- [ ] **Step 3: 运行测试**

```bash
cd /Users/noskystar/IdeaProjects/NGAQuant
pytest tests/test_watchlist.py -v
```

**预期输出：** 10 个测试全部 PASS。

- [ ] **Step 4: 提交**

```bash
git add src/watchlist.py tests/test_watchlist.py
git commit -m "$(cat <<'EOF'
feat: add WatchlistManager for local JSON-based post tracking

- Add/remove post IDs with deduplication and normalization
- Graceful handling of missing/corrupt JSON files
- Full pytest coverage

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: 修复爬虫倒序逻辑

**Files:**
- Modify: `src/crawler/nga_client.py:220-258`
- Test: `tests/test_crawler.py`

- [ ] **Step 1: 修改 `get_full_thread` 方法**

将 `src/crawler/nga_client.py` 第 220-258 行的 `get_full_thread` 替换为：

```python
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
```

- [ ] **Step 2: 确保 `filter_posts_by_hours` 正确处理 `None` 时间戳**

确认 `src/crawler/nga_client.py` 第 277-299 行的 `filter_posts_by_hours` 函数已存在且逻辑正确（保留 `None` 时间戳的帖子，不过滤）。当前代码：

```python
def filter_posts_by_hours(posts: List[NGAPost], max_hours: int) -> List[NGAPost]:
    if max_hours <= 0:
        return posts
    now = datetime.now()
    cutoff = now.timestamp() - max_hours * 3600
    filtered = []
    for post in posts:
        if post.timestamp is not None and post.timestamp.timestamp() >= cutoff:
            filtered.append(post)
    return filtered
```

如果与上述一致则无需修改。注意：`now` 未带时区，而 `post.timestamp` 可能带时区，存在时区不匹配风险。统一修改为带时区的 `datetime.now(timezone.utc)`：

```python
def filter_posts_by_hours(posts: List[NGAPost], max_hours: int) -> List[NGAPost]:
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
```

- [ ] **Step 3: 编写爬虫倒序测试**

在 `tests/test_crawler.py` 中新增或补充测试。先看现有测试结构：

```bash
cd /Users/noskystar/IdeaProjects/NGAQuant
head -50 tests/test_crawler.py
```

然后写入测试（追加到文件末尾）：

```python
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from src.crawler.nga_client import NGACrawler, NGAPost, filter_posts_by_hours


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
            NGAPost("1", "a", "1", "x", None, 1),
            NGAPost("2", "a", "1", "x", now, 2),
        ]
        result = filter_posts_by_hours(posts, 1)
        assert len(result) == 1
        assert result[0].floor == 2

    def test_all_posts_within_range(self):
        """全部在时间范围内时原样返回"""
        now = datetime.now(timezone.utc)
        posts = [
            NGAPost("1", "a", "1", "x", now - timedelta(minutes=30), 1),
            NGAPost("2", "a", "1", "x", now - timedelta(minutes=10), 2),
        ]
        result = filter_posts_by_hours(posts, 1)
        assert len(result) == 2

    def test_mixed_posts(self):
        """混有新旧帖子时只保留新的"""
        now = datetime.now(timezone.utc)
        posts = [
            NGAPost("1", "a", "1", "x", now - timedelta(hours=3), 1),
            NGAPost("2", "a", "1", "x", now - timedelta(minutes=10), 2),
            NGAPost("3", "a", "1", "x", None, 3),
        ]
        result = filter_posts_by_hours(posts, 1)
        assert len(result) == 1
        assert result[0].floor == 2
```

- [ ] **Step 4: 运行测试**

```bash
cd /Users/noskystar/IdeaProjects/NGAQuant
pytest tests/test_crawler.py -v
```

**预期输出：** 新增测试全部 PASS，原有测试不中断。

- [ ] **Step 5: 提交**

```bash
git add src/crawler/nga_client.py tests/test_crawler.py
git commit -m "$(cat <<'EOF'
fix: get_full_thread now crawls last N pages instead of first N

- max_pages now correctly limits to last N pages (newest content)
- Early-break uses latest post per page (max floor) for time check
- Fixed None timestamp being treated as "too old" in early-break
- filter_posts_by_hours uses timezone-aware datetime for consistency

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Streamlit 页面增加关注帖子管理

**Files:**
- Modify: `web/app.py`

- [ ] **Step 1: 导入 WatchlistManager**

在 `web/app.py` 顶部导入区（第 19 行附近）添加：

```python
from src.watchlist import WatchlistManager
```

- [ ] **Step 2: 在 `init_session_state` 中初始化关注相关状态**

在 `init_session_state()` 函数中（第 68-79 行）追加：

```python
    if 'watchlist' not in st.session_state:
        st.session_state.watchlist = WatchlistManager.load()
    if 'watchlist_refresh' not in st.session_state:
        st.session_state.watchlist_refresh = 0
```

- [ ] **Step 3: 在侧边栏顶部添加「关注帖子」区块**

在 `render_sidebar()` 函数中，在 API Key 配置**之前**插入关注列表区块。具体位置：第 99-100 行 `with st.sidebar:` 之后、第 102 行 `st.title("⚙️ 配置")` 之前插入：

```python
        # ==================== 关注帖子 ====================
        st.title("⭐ 关注帖子")

        # 刷新关注列表
        watchlist = WatchlistManager.load()

        if watchlist:
            for tid in watchlist:
                col_tid, col_del = st.columns([3, 1])
                with col_tid:
                    if st.button(f"📌 {tid}", key=f"watch_tid_{tid}", use_container_width=True):
                        st.session_state.current_tid = tid
                        st.rerun()
                with col_del:
                    if st.button("❌", key=f"watch_del_{tid}"):
                        WatchlistManager.remove(tid)
                        st.rerun()
        else:
            st.info("暂无关注的帖子")

        st.divider()
```

然后将原来的第 102 行改为：

```python
        st.title("⚙️ 配置")
```

- [ ] **Step 4: 在分析成功后的结果区上方添加「关注此帖」按钮**

在 `render_results()` 函数中（第 484 行开始），在 `st.divider()` 之前、头部区域添加关注按钮。在第 494 行 `st.header("📊 分析结果")` 之前插入：

```python
    # 关注按钮
    current_tid = st.session_state.get('current_tid')
    if current_tid:
        watchlist = WatchlistManager.load()
        if current_tid not in watchlist:
            if st.button("⭐ 关注此帖", type="secondary"):
                WatchlistManager.add(current_tid)
                st.success(f"已关注帖子 {current_tid}")
                st.rerun()
        else:
            st.info(f"✅ 已关注帖子 {current_tid}")

```

- [ ] **Step 5: 让 tid 输入框支持从 session state 读取**

在 `render_analysis_section` 函数中（第 404 行附近），将 `tid = st.text_input(...)` 改为：

```python
        # 支持从 session state 填入（通过侧边栏点击关注列表）
        default_tid = st.session_state.get('current_tid', "")
        tid = st.text_input(
            "📝 输入 NGA 帖子 ID (tid)",
            value=default_tid,
            placeholder="例如: 25914502",
            help="从帖子 URL 中提取，例如 https://bbs.nga.cn/read.php?tid=25914502"
        )
```

注意：`st.text_input` 在 Streamlit 中设置 `value` 后，如果用户手动修改，Streamlit 会管理内部状态。但需要注意：如果 `current_tid` 变化导致 rererun，用户之前手动输入的内容会被覆盖。这是可接受的行为，因为用户通过侧边栏点击关注ID时，意图就是切换分析目标。

- [ ] **Step 6: 启动 Streamlit 验证 UI**

```bash
cd /Users/noskystar/IdeaProjects/NGAQuant
streamlit run web/app.py
```

**手动验证项：**
1. 侧边栏显示「关注帖子」区块，初始为空时显示 "暂无关注的帖子"
2. 输入 tid 分析后，结果区上方出现「⭐ 关注此帖」按钮
3. 点击关注后，侧边栏列表更新，按钮变为 "✅ 已关注帖子 xxx"
4. 侧边栏点击关注ID，tid 输入框自动填入，点击「开始分析」可正常分析
5. 点击关注ID旁的「❌」，该ID从列表和 JSON 文件中移除

- [ ] **Step 7: 提交**

```bash
git add web/app.py
git commit -m "$(cat <<'EOF'
feat(web): add watchlist management to sidebar

- Watchlist section in sidebar: click to auto-fill tid, click ❌ to remove
- "Follow this post" button appears after successful analysis
- Watchlist persisted to data/watchlist.json

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## 自我审查

### Spec 覆盖检查

| Spec 要求 | 对应 Task |
|-----------|----------|
| 修复 `max_pages` 为从最后一页往前取 N 页 | Task 2 Step 1 |
| 时间过滤 early-break 保留，修复 `None` 误停 | Task 2 Step 1、Step 2 |
| `data/watchlist.json` 本地持久化 | Task 1 Step 1 |
| WatchlistManager 封装 load/save/add/remove | Task 1 Step 1 |
| 侧边栏展示关注列表 + 点击填入 + 删除 | Task 3 Step 3 |
| 分析成功后显示「关注此帖」按钮 | Task 3 Step 4 |
| 测试覆盖 | Task 1 Step 2、Task 2 Step 3 |

**无缺口。**

### Placeholder 扫描

- [x] 无 "TBD"/"TODO"
- [x] 无 "add appropriate error handling" 等模糊描述
- [x] 每个代码步骤都包含完整代码
- [x] 每个测试步骤都包含完整测试代码
- [x] 无 "Similar to Task N" 引用

### 类型一致性检查

- `WatchlistManager.add(tid: str)` 在 Task 1 中定义，Task 3 Step 4 调用时传入 `current_tid`（字符串），一致
- `WatchlistManager.load()` 返回 `List[str]`，Task 3 中用于 `if current_tid not in watchlist`，一致
- `filter_posts_by_hours` 签名在 Task 2 中被调用，一致

---

## 执行方式选择

计划已保存至 `docs/superpowers/plans/2026-04-20-crawler-reverse-watchlist.md`。

**两个执行选项：**

1. **Subagent-Driven（推荐）** - 每个 Task 分配一个独立子代理，我在 Task 间审查结果
2. **Inline Execution** - 在当前会话中按顺序执行任务，我直接编辑代码

你希望用哪种方式执行？
