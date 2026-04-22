"""
信号管理器 - 信号的保存、查询、统计
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.recommender.models import StockSignal, SignalStatus, StrategyType, SignalType

logger = logging.getLogger(__name__)

SIGNALS_DIR = Path(__file__).parent.parent.parent / "data" / "signals"
SIGNALS_DIR.mkdir(parents=True, exist_ok=True)


class SignalManager:
    """信号管理器（文件存储）"""

    def __init__(self, signals_dir=SIGNALS_DIR):
        self.signals_dir = signals_dir

    def save(self, signal: StockSignal) -> Path:
        """保存单个信号"""
        fp = self.signals_dir / f"{signal.signal_id}.json"
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(signal.to_dict(), f, ensure_ascii=False, indent=2)
        return fp

    def save_batch(self, signals: List[StockSignal]) -> List[Path]:
        """批量保存信号"""
        return [self.save(s) for s in signals]

    def get(self, signal_id: str) -> Optional[StockSignal]:
        """读取单个信号"""
        fp = self.signals_dir / f"{signal_id}.json"
        if not fp.exists():
            return None
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        return self._dict_to_signal(data)

    def list_active(self, strategy: Optional[StrategyType] = None,
                    limit: int = 50) -> List[StockSignal]:
        """列出活跃信号"""
        signals = []
        now = datetime.now()
        for fp in sorted(self.signals_dir.glob("*.json"), reverse=True):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                sig = self._dict_to_signal(data)
                if sig.status != SignalStatus.ACTIVE:
                    continue
                if now >= sig.valid_until:
                    # 自动过期
                    sig.status = SignalStatus.EXPIRED
                    self.save(sig)
                    continue
                if strategy and sig.strategy != strategy:
                    continue
                signals.append(sig)
                if len(signals) >= limit:
                    break
            except Exception:
                continue
        return signals

    def list_all(self, strategy: Optional[StrategyType] = None,
                 status: Optional[SignalStatus] = None,
                 limit: int = 100) -> List[StockSignal]:
        """列出所有信号"""
        signals = []
        for fp in sorted(self.signals_dir.glob("*.json"), reverse=True):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                sig = self._dict_to_signal(data)
                if strategy and sig.strategy != strategy:
                    continue
                if status and sig.status != status:
                    continue
                signals.append(sig)
                if len(signals) >= limit:
                    break
            except Exception:
                continue
        return signals

    def update_status(self, signal_id: str, status: SignalStatus,
                      exit_price: Optional[float] = None,
                      return_pct: Optional[float] = None) -> bool:
        """更新信号状态"""
        sig = self.get(signal_id)
        if not sig:
            return False
        sig.status = status
        if exit_price is not None:
            sig.exit_price = exit_price
        if return_pct is not None:
            sig.return_pct = return_pct
        self.save(sig)
        return True

    def get_top_signals(self, strategy: StrategyType = StrategyType.SHORT,
                        top_n: int = 10) -> List[StockSignal]:
        """获取最强信号"""
        active = self.list_active(strategy=strategy, limit=top_n * 2)
        # 优先 STRONG，其次按综合分
        strong = [s for s in active if s.strength.value == "STRONG"]
        moderate = [s for s in active if s.strength.value == "MODERATE"]
        strong.sort(key=lambda x: x.composite_score, reverse=True)
        moderate.sort(key=lambda x: x.composite_score, reverse=True)
        return (strong + moderate)[:top_n]

    def _dict_to_signal(self, data: dict) -> StockSignal:
        """从字典还原 StockSignal"""
        from src.recommender.models import StockSignal as _Signal
        data['signal_type'] = SignalType(data['signal_type'])
        data['strategy'] = StrategyType(data['strategy'])
        data['strength'] = data['strength']  # str 直接用
        data['status'] = SignalStatus(data['status'])
        data['generated_at'] = datetime.fromisoformat(data['generated_at'])
        data['valid_until'] = datetime.fromisoformat(data['valid_until'])
        if data.get('hit_price'):
            data['hit_price'] = float(data['hit_price'])
        if data.get('exit_price'):
            data['exit_price'] = float(data['exit_price'])
        if data.get('return_pct'):
            data['return_pct'] = float(data['return_pct'])
        return StockSignal(**{k: v for k, v in data.items()
                               if k in StockSignal.__dataclass_fields__})
