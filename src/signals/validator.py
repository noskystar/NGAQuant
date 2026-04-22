"""
信号验证器 - 每日收盘后验证信号表现
"""
import logging
from datetime import datetime
from typing import List

from src.recommender.models import SignalType, SignalStatus, StrategyType
from src.prices.fetcher import PriceFetcher

logger = logging.getLogger(__name__)


class SignalValidator:
    """信号验证器"""

    # 止盈止损阈值
    SHORT_STOP_PROFIT = 0.08   # 短线止盈 8%
    SHORT_STOP_LOSS = 0.05     # 短线止损 5%
    MID_STOP_PROFIT = 0.15     # 中线止盈 15%
    MID_STOP_LOSS = 0.10      # 中线止损 10%

    def __init__(self):
        self.fetcher = PriceFetcher()

    def validate_all(self, signals: List) -> dict:
        """
        验证所有活跃信号

        Returns:
            dict: {"checked": N, "hit": M, "expired": K, "stopped": J}
        """
        stats = {"checked": 0, "hit": 0, "expired": 0, "stopped": 0}

        for sig in signals:
            if sig.status != SignalStatus.ACTIVE:
                continue

            stats["checked"] += 1

            # 检查是否过期
            if datetime.now() >= sig.valid_until:
                sig.status = SignalStatus.EXPIRED
                sig.exit_price = None
                sig.return_pct = 0.0
                stats["expired"] += 1
                continue

            # 获取最新价格
            price_data = self.fetcher.get_realtime(sig.stock_code)
            if not price_data or not price_data.get('price'):
                continue

            current_price = price_data['price']
            entry_price = sig.hit_price or price_data.get('open') or current_price

            if sig.hit_price is None:
                # 尚未入场：检查是否触发入场
                if self._should_enter(sig, entry_price, current_price):
                    sig.hit_price = entry_price
                    sig.status = SignalStatus.HIT
                    stats["hit"] += 1
            else:
                # 已入场：检查是否触发止盈/止损
                exited, reason = self._should_exit(sig, entry_price, current_price)
                if exited:
                    sig.exit_price = current_price
                    sig.return_pct = round((current_price - entry_price) / entry_price * 100, 2)
                    sig.status = SignalStatus.STOPPED
                    sig.reason["exit_reason"] = reason
                    stats["stopped"] += 1

        return stats

    def _should_enter(self, sig, entry_price: float, current_price: float) -> bool:
        """检查是否应入场"""
        if sig.signal_type == SignalType.BUY:
            return current_price >= entry_price  # 价格不低于开盘价
        elif sig.signal_type == SignalType.ACCUMULATE:
            return True  # 中线布局直接入场
        return False

    def _should_exit(self, sig, entry_price: float, current_price: float) -> tuple:
        """检查是否应出场，返回 (是否出场, 出场原因)"""
        ret_pct = (current_price - entry_price) / entry_price
        threshold = (self.SHORT_STOP_PROFIT if sig.strategy == StrategyType.SHORT
                     else self.MID_STOP_PROFIT)
        loss_threshold = (self.SHORT_STOP_LOSS if sig.strategy == StrategyType.SHORT
                          else self.MID_STOP_LOSS)

        if ret_pct >= threshold:
            return True, f"止盈({ret_pct*100:.1f}% ≥ {threshold*100:.1f}%)"
        if ret_pct <= -loss_threshold:
            return True, f"止损({ret_pct*100:.1f}% ≤ {-loss_threshold*1e2:.1f}%)"
        return False, ""
