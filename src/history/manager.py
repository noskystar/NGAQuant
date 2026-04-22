"""
历史记录管理器 - 保存和读取帖子分析结果
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict


HISTORY_DIR = Path(__file__).parent.parent.parent / "data" / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class StockMention:
    """股票提及"""
    name: str
    code: str
    market: str  # SH/SZ
    mention_count: int


@dataclass
class SentimentSummary:
    """情绪摘要（来自聚合结果）"""
    emotion_index: float  # 0-100，50为中性
    emotion_label: str   # 贪婪/中性/恐惧等
    bullish_ratio: float
    neutral_ratio: float
    bearish_ratio: float
    avg_confidence: float


@dataclass
class AnalysisRecord:
    """单次分析记录"""
    tid: str
    analyzed_at: str       # ISO 格式时间
    total_posts: int       # 总帖子数
    valid_posts: int       # 有效帖子数
    pages_parsed: int      # 爬取页数
    emotion: SentimentSummary
    top_stocks: List[StockMention]  # Top 10 热门股票
    key_posts_summary: List[str]   # 关键帖子摘要（前5条）

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # 序列化时去掉 dataclass 嵌套标记
        return d

    def save(self) -> Path:
        """保存到 JSON 文件"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.tid}_{ts}.json"
        filepath = HISTORY_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return filepath


class HistoryManager:
    """历史记录管理器"""

    def __init__(self, history_dir: Path = HISTORY_DIR):
        self.history_dir = history_dir

    def _get_record_files(self, tid: Optional[str] = None) -> List[Path]:
        """获取历史记录文件"""
        if tid:
            pattern = f"{tid}_*.json"
        else:
            pattern = "*.json"
        files = sorted(self.history_dir.glob(pattern), reverse=True)
        return files

    def list_records(self, tid: Optional[str] = None, limit: int = 20) -> List[AnalysisRecord]:
        """列出历史记录"""
        records = []
        for fp in self._get_record_files(tid)[:limit]:
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                records.append(AnalysisRecord(**data))
            except Exception:
                continue
        return records

    def get_record(self, tid: str, index: int = 0) -> Optional[AnalysisRecord]:
        """获取某帖子的第 index 条历史记录（0=最新）"""
        records = self.list_records(tid=tid, limit=index + 1)
        if len(records) > index:
            return records[index]
        return None

    def get_latest(self, tid: str) -> Optional[AnalysisRecord]:
        """获取某帖子的最新分析记录"""
        return self.get_record(tid, index=0)

    def get_previous(self, tid: str) -> Optional[AnalysisRecord]:
        """获取某帖子的上次分析记录"""
        return self.get_record(tid, index=1)

    def get_trend(self, tid: str, limit: int = 10) -> Dict[str, Any]:
        """获取某帖子的情绪变化趋势"""
        records = self.list_records(tid=tid, limit=limit)
        if not records:
            return {"error": f"没有 {tid} 的历史记录"}

        trend = {
            "tid": tid,
            "count": len(records),
            "records": []
        }

        for i, rec in enumerate(records):
            rec_data = {
                "analyzed_at": rec.analyzed_at,
                "emotion_index": rec.emotion.emotion_index,
                "emotion_label": rec.emotion.emotion_label,
                "bullish_ratio": rec.emotion.bullish_ratio,
                "bearish_ratio": rec.emotion.bearish_ratio,
                "top_stocks": [(s.name, s.code, s.mention_count) for s in rec.top_stocks[:5]],
            }

            # 与上次对比
            if i == 0 and len(records) > 1:
                prev = records[1]
                diff = rec.emotion.emotion_index - prev.emotion.emotion_index
                rec_data["vs_previous"] = {
                    "emotion_diff": round(diff, 1),
                    "direction": "↑" if diff > 0 else "↓" if diff < 0 else "→",
                }
                # 股票变化
                prev_stocks = {s.code: s for s in prev.top_stocks}
                curr_stocks = {s.code: s for s in rec.top_stocks}
                new_stocks = set(curr_stocks.keys()) - set(prev_stocks.keys())
                gone_stocks = set(prev_stocks.keys()) - set(curr_stocks.keys())
                rec_data["stocks_changes"] = {
                    "new": [curr_stocks[c].name for c in new_stocks],
                    "gone": [prev_stocks[c].name for c in gone_stocks],
                }

            trend["records"].append(rec_data)

        return trend

    def save_analysis(
        self,
        tid: str,
        total_posts: int,
        valid_posts: int,
        pages_parsed: int,
        emotion_data: Dict[str, Any],
        top_stocks: List[Any],
        key_posts: List[str],
    ) -> Path:
        """
        保存一次分析结果

        Args:
            tid: 帖子ID
            total_posts: 总帖子数
            valid_posts: 有效帖子数
            pages_parsed: 爬取页数
            emotion_data: SentimentAggregator.aggregate() 返回的字典
            top_stocks: Stock 对象列表
            key_posts: 关键帖子摘要列表
        """
        sentiment = SentimentSummary(
            emotion_index=emotion_data.get("emotion_index", 50.0),
            emotion_label=emotion_data.get("market_emotion", "未知"),
            bullish_ratio=emotion_data.get("bullish_ratio", 0.0),
            neutral_ratio=emotion_data.get("neutral_ratio", 0.0),
            bearish_ratio=emotion_data.get("bearish_ratio", 0.0),
            avg_confidence=emotion_data.get("avg_confidence", 0.0),
        )

        stock_mentions = [
            StockMention(
                name=s.name,
                code=s.code,
                market=s.market,
                mention_count=s.mention_count,
            )
            for s in top_stocks[:10]
        ]

        record = AnalysisRecord(
            tid=tid,
            analyzed_at=datetime.now().isoformat(),
            total_posts=total_posts,
            valid_posts=valid_posts,
            pages_parsed=pages_parsed,
            emotion=sentiment,
            top_stocks=stock_mentions,
            key_posts_summary=key_posts[:5],
        )

        return record.save()
