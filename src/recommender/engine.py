"""
推荐引擎 - 双因子融合算法主入口
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .models import StockSignal, SignalType, SignalStrength, SignalStatus, StrategyType
from .strategies import ShortTermStrategy, MidTermStrategy
from src.prices.fetcher import PriceFetcher
from src.prices.indicators import calculate_indicators
from src.prices.factor import PriceFactor

logger = logging.getLogger(__name__)


class RecommenderEngine:
    """
    双因子推荐引擎

    输入: 帖子分析结果（情绪指数、热门股票列表）+ 股票价格数据
    输出: 推荐信号列表
    """

    def __init__(self):
        self.fetcher = PriceFetcher()
        self.price_factor = PriceFactor()

    def generate_signals(
        self,
        emotion_index: float,
        emotion_trend_3d: Optional[List[float]],  # 近3次情绪指数列表
        top_stocks: List[Dict[str, Any]],  # [{"name": "贵州茅台", "code": "600519", "mention_count": 5}, ...]
        source_tid: str,
        strategy: StrategyType = StrategyType.SHORT,
    ) -> List[StockSignal]:
        """
        生成推荐信号

        Args:
            emotion_index: 当前情绪指数 0-100
            emotion_trend_3d: 近3次情绪指数（用于中线趋势判断）
            top_stocks: 热门股票列表
            source_tid: 来源帖子ID
            strategy: SHORT 或 MID

        Returns:
            StockSignal 列表（按 composite_score 降序）
        """
        reverse_emotion = 100 - emotion_index
        signals: List[StockSignal] = []

        for stock in top_stocks:
            code = stock.get('code')
            name = stock.get('name', code)
            mention_count = stock.get('mention_count', 1)

            if not code:
                continue

            # 获取价格数据
            df = self.fetcher.get_daily(code, period="daily", adjust="qfq")
            if df is None or len(df) < 20:
                logger.debug(f"{code} {name} 价格数据不足，跳过")
                continue

            df = calculate_indicators(df)
            pf = self.price_factor.calculate(df)

            if strategy == StrategyType.SHORT:
                sig = self._generate_short_signal(
                    code, name, reverse_emotion, pf,
                    mention_count, source_tid
                )
            else:
                sig = self._generate_mid_signal(
                    code, name, reverse_emotion, pf,
                    emotion_trend_3d or [emotion_index] * 3,
                    mention_count, source_tid
                )

            if sig:
                signals.append(sig)

        # 按综合分降序
        signals.sort(key=lambda x: x.composite_score, reverse=True)
        return signals

    def _generate_short_signal(
        self, code: str, name: str,
        reverse_emotion: float, pf: Dict,
        mention_count: int, source_tid: str
    ) -> Optional[StockSignal]:
        """生成短线信号"""
        price_factor = pf['score']
        change_pct = pf['change_pct']
        valid_days = 3

        # 优先检查买入
        is_buy, buy_reason = ShortTermStrategy.check_buy(
            reverse_emotion, price_factor, change_pct, mention_count
        )
        if is_buy:
            composite = ShortTermStrategy.composite_score(reverse_emotion, price_factor)
            return StockSignal(
                stock_code=code,
                stock_name=name,
                signal_type=SignalType.BUY,
                strategy=StrategyType.SHORT,
                emotion_index=100 - reverse_emotion,
                reverse_emotion_score=reverse_emotion,
                price_factor=price_factor,
                composite_score=composite,
                strength=ShortTermStrategy.strength(composite),
                reason={
                    "trigger": "短线买入",
                    "emotion_reason": buy_reason,
                    "price_data": {
                        "close": pf['close'],
                        "change_pct": change_pct,
                        "rsi": pf['rsi'],
                        "ma5": pf['ma5'],
                        "ma20": pf['ma20'],
                        "volume_ratio": pf['volume_ratio'],
                    },
                    "mention_count": mention_count,
                },
                source_tid=source_tid,
                generated_at=datetime.now(),
                valid_until=datetime.now() + timedelta(days=valid_days),
            )

        # 检查卖出
        is_sell, sell_reason = ShortTermStrategy.check_sell(
            reverse_emotion, price_factor, change_pct
        )
        if is_sell:
            composite = ShortTermStrategy.composite_score(reverse_emotion, price_factor)
            return StockSignal(
                stock_code=code,
                stock_name=name,
                signal_type=SignalType.SELL,
                strategy=StrategyType.SHORT,
                emotion_index=100 - reverse_emotion,
                reverse_emotion_score=reverse_emotion,
                price_factor=price_factor,
                composite_score=composite,
                strength=ShortTermStrategy.strength(composite),
                reason={
                    "trigger": "短线卖出/回避",
                    "emotion_reason": sell_reason,
                    "price_data": {
                        "close": pf['close'],
                        "change_pct": change_pct,
                        "rsi": pf['rsi'],
                    },
                    "mention_count": mention_count,
                },
                source_tid=source_tid,
                generated_at=datetime.now(),
                valid_until=datetime.now() + timedelta(days=valid_days),
            )

        return None

    def _generate_mid_signal(
        self, code: str, name: str,
        reverse_emotion: float, pf: Dict,
        emotion_trend_3d: List[float],
        mention_count: int, source_tid: str
    ) -> Optional[StockSignal]:
        """生成中线信号"""
        price_factor = pf['score']
        rsi = pf['rsi']
        volume_ratio = pf['volume_ratio']
        valid_days = 28

        # 情绪均线
        emotion_ma3_prev = sum(emotion_trend_3d[-2:]) / 2 if len(emotion_trend_3d) >= 2 else emotion_trend_3d[0]
        emotion_trend_str = "rising" if emotion_trend_3d[-1] > emotion_ma3_prev else "falling"

        # 布局检查
        is_accum, accum_reason = MidTermStrategy.check_accumulate(
            emotion_trend_str, 100 - reverse_emotion,
            emotion_ma3_prev, price_factor, rsi, volume_ratio
        )
        if is_accum:
            composite = MidTermStrategy.composite_score(reverse_emotion, price_factor)
            return StockSignal(
                stock_code=code,
                stock_name=name,
                signal_type=SignalType.ACCUMULATE,
                strategy=StrategyType.MID,
                emotion_index=100 - reverse_emotion,
                reverse_emotion_score=reverse_emotion,
                price_factor=price_factor,
                composite_score=composite,
                strength=MidTermStrategy.strength(composite),
                reason={
                    "trigger": "中线布局",
                    "emotion_reason": accum_reason,
                    "price_data": {
                        "close": pf['close'],
                        "rsi": rsi,
                        "volume_ratio": volume_ratio,
                        "ma5": pf['ma5'],
                        "ma20": pf['ma20'],
                        "breakout": pf['breakout'],
                    },
                    "emotion_trend_3d": emotion_trend_3d,
                    "mention_count": mention_count,
                },
                source_tid=source_tid,
                generated_at=datetime.now(),
                valid_until=datetime.now() + timedelta(days=valid_days),
            )

        # 减仓检查
        is_reduce, reduce_reason = MidTermStrategy.check_reduce(
            emotion_trend_str, 100 - reverse_emotion,
            emotion_ma3_prev, price_factor, rsi
        )
        if is_reduce:
            composite = MidTermStrategy.composite_score(reverse_emotion, price_factor)
            return StockSignal(
                stock_code=code,
                stock_name=name,
                signal_type=SignalType.REDUCE,
                strategy=StrategyType.MID,
                emotion_index=100 - reverse_emotion,
                reverse_emotion_score=reverse_emotion,
                price_factor=price_factor,
                composite_score=composite,
                strength=MidTermStrategy.strength(composite),
                reason={
                    "trigger": "中线减仓",
                    "emotion_reason": reduce_reason,
                    "price_data": {"close": pf['close'], "rsi": rsi},
                    "emotion_trend_3d": emotion_trend_3d,
                },
                source_tid=source_tid,
                generated_at=datetime.now(),
                valid_until=datetime.now() + timedelta(days=valid_days),
            )

        return None

    def generate_all_signals(
        self,
        posts_data: List[Dict[str, Any]],  # [{"tid": "", "emotion_index": 60.0, "top_stocks": [...]}]
        strategy: StrategyType = StrategyType.SHORT,
    ) -> List[StockSignal]:
        """
        聚合多个帖子数据生成综合信号

        Args:
            posts_data: 多个帖子的分析结果
            strategy: SHORT 或 MID

        Returns:
            合并后的信号列表（去重，按 score 排序）
        """
        all_signals: Dict[str, StockSignal] = {}

        for post in posts_data:
            emotion_index = post.get('emotion_index', 50.0)
            emotion_trend = post.get('emotion_trend_3d', [emotion_index] * 3)
            top_stocks = post.get('top_stocks', [])
            tid = post.get('tid', 'unknown')

            signals = self.generate_signals(
                emotion_index=emotion_index,
                emotion_trend_3d=emotion_trend,
                top_stocks=top_stocks,
                source_tid=tid,
                strategy=strategy,
            )

            for sig in signals:
                # 同股票多帖子取高分
                if sig.stock_code not in all_signals or \
                   sig.composite_score > all_signals[sig.stock_code].composite_score:
                    all_signals[sig.stock_code] = sig

        result = list(all_signals.values())
        result.sort(key=lambda x: x.composite_score, reverse=True)
        return result
