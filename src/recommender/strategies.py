"""
短线/中线推荐策略规则
"""
from typing import Tuple
from .models import SignalType, SignalStrength


class ShortTermStrategy:
    """短线策略（持仓 1-3 天）"""

    # 短线权重
    ALPHA = 0.45   # 情绪因子权重
    BETA = 0.55    # 价格因子权重

    # 买入阈值
    BUY_REVERSE_EMOTION_MIN = 70  # 反向情绪分 >= 70（情绪极度恐惧）
    BUY_PRICE_FACTOR_MIN = 60     # 价格因子 >= 60（技术面不弱）
    BUY_MAX_RISE_PCT = 5.0        # 当日涨幅 < 5%（避免追高）
    BUY_MIN_MENTIONS = 3           # 近 N 次分析中被提及 >= 3 次

    # 卖出阈值
    SELL_REVERSE_EMOTION_MAX = 30  # 反向情绪分 <= 30（情绪极度贪婪）
    SELL_PRICE_FACTOR_MAX = 40     # 价格因子 <= 40（技术面滞涨）
    SELL_MAX_DROP_PCT = -3.0       # 当日跌幅 > -3%（避免杀跌在底部）

    @classmethod
    def check_buy(cls, reverse_emotion: float, price_factor: float,
                  change_pct: float, mention_count: int) -> Tuple[bool, str]:
        """检查是否满足短线买入条件"""
        reasons = []

        if reverse_emotion >= cls.BUY_REVERSE_EMOTION_MIN:
            reasons.append(f"情绪恐惧({reverse_emotion:.1f} ≥ {cls.BUY_REVERSE_EMOTION_MIN})")
        else:
            return False, f"情绪不够恐惧({reverse_emotion:.1f})"

        if price_factor >= cls.BUY_PRICE_FACTOR_MIN:
            reasons.append(f"技术面支撑({price_factor:.1f} ≥ {cls.BUY_PRICE_FACTOR_MIN})")
        else:
            return False, f"技术面偏弱({price_factor:.1f})"

        if change_pct < cls.BUY_MAX_RISE_PCT:
            reasons.append(f"未过度上涨(涨幅{change_pct:.1f}%)")
        else:
            return False, f"已过度上涨({change_pct:.1f}%), 存在回调风险"

        if mention_count >= cls.BUY_MIN_MENTIONS:
            reasons.append(f"关注度高(提及{mention_count}次)")
        else:
            return False, f"关注度不足(仅{mention_count}次)"

        return True, "; ".join(reasons)

    @classmethod
    def check_sell(cls, reverse_emotion: float, price_factor: float,
                   change_pct: float) -> Tuple[bool, str]:
        """检查是否满足短线卖出/回避条件"""
        reasons = []

        if reverse_emotion <= cls.SELL_REVERSE_EMOTION_MAX:
            reasons.append(f"情绪贪婪({reverse_emotion:.1f} ≤ {cls.SELL_REVERSE_EMOTION_MAX})")
        else:
            return False, f"情绪未到贪婪区({reverse_emotion:.1f})"

        if price_factor <= cls.SELL_PRICE_FACTOR_MAX:
            reasons.append(f"技术面走弱({price_factor:.1f} ≤ {cls.SELL_PRICE_FACTOR_MAX})")
        else:
            return False, f"技术面仍强({price_factor:.1f})"

        if change_pct > cls.SELL_MAX_DROP_PCT:
            reasons.append(f"未跌过度(跌幅{change_pct:.1f}%)")
        else:
            return False, f"已在低位({change_pct:.1f}%), 不宜杀跌"

        return True, "; ".join(reasons)

    @classmethod
    def composite_score(cls, reverse_emotion: float, price_factor: float) -> float:
        """计算综合信号分"""
        return round(cls.ALPHA * reverse_emotion + cls.BETA * price_factor, 1)

    @classmethod
    def strength(cls, score: float) -> SignalStrength:
        if score >= 85:
            return SignalStrength.STRONG
        elif score >= 70:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK


class MidTermStrategy:
    """中线策略（持仓 1-4 周）"""

    ALPHA = 0.55   # 情绪因子权重（中线更重视情绪趋势）
    BETA = 0.45    # 价格因子权重

    # 布局阈值
    ACCUM_EMOTION_TREND_RISE = True    # 情绪均线从低位回升
    ACCUM_EMOTION_CROSS = True          # 情绪指数上穿均线
    ACCUM_PRICE_BREAKOUT = True         # 价格突破 MA20
    ACCUM_RSI_FROM_OVERSOLD = True     # RSI 从超卖区回升至 40 以上
    ACCUM_VOLUME_RATIO_MIN = 1.2        # 成交量 >= 20日均量 1.2 倍

    # 减仓阈值
    REDUCE_EMOTION_TREND_FALL = True   # 情绪均线从高位回落
    REDUCE_PRICE_BELOW_MA10 = True     # 价格跌破 MA10

    @classmethod
    def check_accumulate(cls, emotion_trend: str, emotion_index: float,
                          emotion_ma3_prev: float, price_factor: float,
                          rsi: float, volume_ratio: float) -> Tuple[bool, str]:
        """检查是否满足中线布局条件"""
        reasons = []

        # 情绪趋势
        if emotion_index > 35 and emotion_index > emotion_ma3_prev:
            reasons.append(f"情绪回升({emotion_index:.1f} > 均线{emotion_ma3_prev:.1f})")
        else:
            return False, f"情绪未回升({emotion_index:.1f})"

        # RSI
        if rsi > 40:
            reasons.append(f"RSI健康({rsi:.1f} > 40)")
        else:
            return False, f"RSI偏弱({rsi:.1f})"

        # 量价（量能不足直接拒绝）
        if volume_ratio < cls.ACCUM_VOLUME_RATIO_MIN:
            return False, f"量能不足(量比{volume_ratio:.1f} < {cls.ACCUM_VOLUME_RATIO_MIN})"
        reasons.append(f"量能放大(量比{volume_ratio:.1f})")

        return True, "; ".join(reasons)

    @classmethod
    def check_reduce(cls, emotion_trend: str, emotion_index: float,
                      emotion_ma3_prev: float, price_factor: float,
                      rsi: float) -> Tuple[bool, str]:
        """检查是否满足中线减仓条件"""
        reasons = []

        if emotion_index < 65 and emotion_index < emotion_ma3_prev:
            reasons.append(f"情绪回落({emotion_index:.1f} < 均线{emotion_ma3_prev:.1f})")
        else:
            return False, f"情绪未明显回落({emotion_index:.1f})"

        if rsi < 60:
            reasons.append(f"RSI偏高后回落({rsi:.1f})")
        else:
            return False, f"RSI仍强({rsi:.1f})"

        return True, "; ".join(reasons)

    @classmethod
    def composite_score(cls, reverse_emotion: float, price_factor: float) -> float:
        return round(cls.ALPHA * reverse_emotion + cls.BETA * price_factor, 1)

    @classmethod
    def strength(cls, score: float) -> SignalStrength:
        if score >= 82:
            return SignalStrength.STRONG
        elif score >= 68:
            return SignalStrength.MODERATE
        else:
            return SignalStrength.WEAK
