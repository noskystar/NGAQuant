"""
价格因子评分 - 将技术指标融合为 0-100 的价格因子分
"""
import pandas as pd
from typing import Optional
from .indicators import trend_score, momentum_score, volume_score, price_breakout


class PriceFactor:
    """价格因子计算机"""

    @staticmethod
    def calculate(df: pd.DataFrame) -> dict:
        """
        计算价格因子评分

        Args:
            df: 含技术指标的日线 DataFrame（最新一条为最近交易日）

        Returns:
            dict with keys:
                - score: 总分 0-100
                - trend: 趋势分 0-40
                - momentum: 动量分 0-30
                - volume: 量价分 0-30
                - rsi: RSI(14) 当前值
                - ma5, ma10, ma20, ma60: 均线值
                - close: 最新收盘价
                - change_pct: 当日涨跌幅
                - breakout: 是否突破 MA20
                - volume_ratio: 量比（当日量/20日均量）
        """
        if df is None or len(df) < 5:
            return PriceFactor._default()

        latest = df.iloc[-1]
        close = float(latest.get('close', 0) or 0)
        if close <= 0:
            return PriceFactor._default()

        trend = trend_score(df)
        momentum = momentum_score(df)
        volume_s = volume_score(df)
        total = min(100, trend + momentum + volume_s)

        # 量比
        vol = float(latest.get('volume', 0) or 0)
        vol_ma20 = float(latest.get('volume_ma20', 0) or 0)
        vol_ratio = vol / vol_ma20 if vol_ma20 > 0 else 1.0

        return {
            'score': round(total, 1),
            'trend': round(trend, 1),
            'momentum': round(momentum, 1),
            'volume': round(volume_s, 1),
            'rsi': round(float(latest.get('rsi_14', 50) or 50), 1),
            'ma5': round(float(latest.get('ma5', 0) or 0), 2),
            'ma10': round(float(latest.get('ma10', 0) or 0), 2),
            'ma20': round(float(latest.get('ma20', 0) or 0), 2),
            'ma60': round(float(latest.get('ma60', 0) or 0), 2) if 'ma60' in latest else None,
            'close': round(close, 2),
            'change_pct': round(float(latest.get('change_pct', 0) or 0), 2),
            'breakout': price_breakout(df),
            'volume_ratio': round(vol_ratio, 2),
        }

    @staticmethod
    def _default() -> dict:
        return {
            'score': 50.0, 'trend': 15.0, 'momentum': 15.0, 'volume': 15.0,
            'rsi': 50.0, 'ma5': 0, 'ma10': 0, 'ma20': 0, 'ma60': 0,
            'close': 0, 'change_pct': 0, 'breakout': False, 'volume_ratio': 1.0,
        }
