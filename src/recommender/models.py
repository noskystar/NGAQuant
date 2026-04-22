"""
推荐信号数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
from enum import Enum
import uuid


class SignalType(str, Enum):
    BUY = "BUY"        # 短线买入
    SELL = "SELL"      # 短线卖出/回避
    ACCUMULATE = "ACCUMULATE"  # 中线布局
    REDUCE = "REDUCE"  # 中线减仓
    HOLD = "HOLD"      # 持有/观望


class StrategyType(str, Enum):
    SHORT = "SHORT"   # 短线 1-3天
    MID = "MID"       # 中线 1-4周


class SignalStrength(str, Enum):
    STRONG = "STRONG"     # 强信号
    MODERATE = "MODERATE" # 中等信号
    WEAK = "WEAK"         # 弱信号（仅观察）


class SignalStatus(str, Enum):
    ACTIVE = "ACTIVE"     # 活跃中
    HIT = "HIT"          # 已触发（已入场）
    EXPIRED = "EXPIRED"  # 已过期
    STOPPED = "STOPPED"  # 已止损/止盈退出


@dataclass
class StockSignal:
    """个股推荐信号"""
    stock_code: str
    stock_name: str
    signal_type: SignalType
    strategy: StrategyType
    emotion_index: float        # 情绪指数 0-100
    reverse_emotion_score: float  # 反向情绪分 = 100 - emotion_index
    price_factor: float         # 价格因子分 0-100
    composite_score: float       # 综合信号分 0-100
    strength: SignalStrength
    reason: dict               # 信号生成理由详情
    source_tid: str            # 来源帖子ID
    generated_at: datetime
    valid_until: datetime
    status: SignalStatus = SignalStatus.ACTIVE
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    hit_price: Optional[float] = None
    exit_price: Optional[float] = None
    return_pct: Optional[float] = None

    @property
    def is_active(self) -> bool:
        return self.status == SignalStatus.ACTIVE and datetime.now() < self.valid_until

    @property
    def emoji(self) -> str:
        return {
            SignalType.BUY: "🟢",
            SignalType.SELL: "🔴",
            SignalType.ACCUMULATE: "🟡",
            SignalType.REDUCE: "⚠️",
            SignalType.HOLD: "⬜",
        }.get(self.signal_type, "❓")

    def to_dict(self) -> dict:
        return {
            "signal_id": self.signal_id,
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "signal_type": self.signal_type.value,
            "strategy": self.strategy.value,
            "emotion_index": self.emotion_index,
            "reverse_emotion_score": self.reverse_emotion_score,
            "price_factor": self.price_factor,
            "composite_score": self.composite_score,
            "strength": self.strength.value,
            "reason": self.reason,
            "source_tid": self.source_tid,
            "generated_at": self.generated_at.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "status": self.status.value,
            "hit_price": self.hit_price,
            "exit_price": self.exit_price,
            "return_pct": self.return_pct,
        }
