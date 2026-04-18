# 数据模型
"""
数据存储模型
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional
import json

@dataclass
class Post:
    """帖子模型"""
    post_id: str
    tid: str
    author: str
    author_uid: str
    content: str
    timestamp: datetime
    floor: int
    is_main_post: bool = False
    sentiment: Optional[str] = None
    sentiment_confidence: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "post_id": self.post_id,
            "tid": self.tid,
            "author": self.author,
            "author_uid": self.author_uid,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "floor": self.floor,
            "is_main_post": self.is_main_post,
            "sentiment": self.sentiment,
            "sentiment_confidence": self.sentiment_confidence
        }

@dataclass
class AnalysisReport:
    """分析报告模型"""
    id: str
    tid: str
    timestamp: datetime
    total_posts: int
    emotion_index: float
    market_emotion: str
    bullish_ratio: float
    bearish_ratio: float
    neutral_ratio: float
    avg_confidence: float
    top_stocks: List[dict]
    recommendation: str
    raw_data: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tid": self.tid,
            "timestamp": self.timestamp.isoformat(),
            "total_posts": self.total_posts,
            "emotion_index": self.emotion_index,
            "market_emotion": self.market_emotion,
            "bullish_ratio": self.bullish_ratio,
            "bearish_ratio": self.bearish_ratio,
            "neutral_ratio": self.neutral_ratio,
            "avg_confidence": self.avg_confidence,
            "top_stocks": self.top_stocks,
            "recommendation": self.recommendation
        }
    
    def save_to_file(self, output_dir: str = "output"):
        """保存到文件"""
        import os
        from pathlib import Path
        
        Path(output_dir).mkdir(exist_ok=True)
        
        filename = f"{self.tid}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(output_dir) / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        return filepath
