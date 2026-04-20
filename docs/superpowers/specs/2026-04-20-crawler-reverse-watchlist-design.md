# NGAQuant 爬虫修复 + 关注帖子管理 设计文档

## 背景

1. **爬虫倒序 bug**：`get_full_thread` 的 `max_pages` 参数逻辑错误。当帖子有 100 页、设 `max_pages=5` 时，当前代码爬取的是第 1~5 页（最旧内容），而非用户期望的第 96~100 页（最新内容）。
2. **关注帖子需求**：用户希望图形化保存关注的帖子 ID，便于反复查看分析结果。

## 目标

1. 修复爬虫，使 `max_pages` 真正限制为「从最后一页往前取 N 页」
2. 增加关注帖子管理功能，无需数据库，通过本地 JSON 文件持久化

## 方案

### 1. 爬虫倒序修复

**修复文件**：`src/crawler/nga_client.py`

**当前逻辑（bug）**：
```python
total_pages = self.get_total_pages(tid)
if max_pages:
    total_pages = min(total_pages, max_pages)  # 限制总页数为 N
for page in range(total_pages, 0, -1):         # 从 N 倒序到 1
```

**修复后逻辑**：
```python
total_pages = self.get_total_pages(tid)
start_page = total_pages
end_page = 1
if max_pages:
    end_page = max(1, total_pages - max_pages + 1)  # 只取最后 N 页
for page in range(start_page, end_page - 1, -1):
```

**时间过滤优化**：
- 当前代码判断整页是否超时使用 `all()`，其中 `p.timestamp` 为 `None`（解析失败）时被当作 "已超时"（`else True`），可能导致提前误停
- **改为**：用该页**最新的一条帖子**判断（楼层号最大 = 时间最新），若最新帖子都已超时则整页确实已超时，可安全 `break`；`None` 时间戳不参与超时判断
- 保持 early-break 机制不变——它是有效优化，避免无意义爬取

### 2. 关注帖子管理

**数据持久化**
- 文件路径：`data/watchlist.json`
- 格式：`{"ids": ["25914502", "42000001"]}`
- 目录不存在时自动创建

**封装模块**：`src/watchlist.py`

```python
import json
import os
from typing import List

WATCHLIST_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "watchlist.json")

class WatchlistManager:
    @staticmethod
    def _ensure_dir():
        os.makedirs(os.path.dirname(WATCHLIST_PATH), exist_ok=True)

    @staticmethod
    def load() -> List[str]:
        if not os.path.exists(WATCHLIST_PATH):
            return []
        try:
            with open(WATCHLIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get("ids", [])
        except (json.JSONDecodeError, IOError):
            return []

    @staticmethod
    def save(ids: List[str]):
        WatchlistManager._ensure_dir()
        with open(WATCHLIST_PATH, "w", encoding="utf-8") as f:
            json.dump({"ids": ids}, f, ensure_ascii=False, indent=2)

    @staticmethod
    def add(tid: str) -> bool:
        ids = WatchlistManager.load()
        normalized = tid.strip()
        if normalized and normalized not in ids:
            ids.append(normalized)
            WatchlistManager.save(ids)
            return True
        return False

    @staticmethod
    def remove(tid: str) -> bool:
        ids = WatchlistManager.load()
        normalized = tid.strip()
        if normalized in ids:
            ids.remove(normalized)
            WatchlistManager.save(ids)
            return True
        return False
```

**Web UI 改动**：`web/app.py`

- **侧边栏新增「关注帖子」区块**：位于 API Key 配置上方
  - 展示当前关注列表（ID 文本 + 可点击填入 + 删除按钮）
  - 点击关注 ID → 自动填入 `tid` 输入框

- **分析完成后增加「关注」按钮**：在 `render_results` 或分析成功后的提示区域上方
  - 若当前 tid 不在关注列表，显示「⭐ 关注此帖」
  - 点击后调用 `WatchlistManager.add()`，列表自动刷新

**交互流程**：
1. 用户输入 tid → 分析完成
2. 结果区上方出现「⭐ 关注此帖」按钮
3. 点击后写入 JSON，侧边栏关注列表自动更新
4. 侧边栏点击已有关注 ID → 自动填入分析框，用户再点「开始分析」

## 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/crawler/nga_client.py` | 修改 | 修复 `get_full_thread` 的 `max_pages` 逻辑；时间过滤改为爬完后统一过滤 |
| `src/watchlist.py` | 新增 | 关注列表 JSON 读写封装 |
| `web/app.py` | 修改 | 侧边栏增加关注列表管理；分析成功后增加关注按钮 |

## 测试要点

1. **爬虫修复**：
   - 对有多页的实际帖子，设 `max_pages=2`，确认只爬最后 2 页
   - `max_pages` 大于总页数时，正常爬取全部
   - `max_pages=0` 或 `None` 时，爬取全部

2. **关注列表**：
   - 添加、删除、重复添加、空输入边界
   - JSON 文件不存在时首次写入正常
   - 文件损坏（非合法 JSON）时优雅降级为空列表

## 非目标（YAGNI）

- 多用户隔离（本地单用户运行，无需考虑）
- 关注帖子的分析历史缓存（仅保存 ID）
- 关注帖子的自动定时分析
- Web 服务器部署时的文件并发写入问题（本地单进程 Streamlit，无此场景）
