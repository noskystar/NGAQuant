"""
技术指标计算 - MA / RSI / MACD / 均线多头排列
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    给日线 DataFrame 计算技术指标（MA5/10/20, RSI, MACD）

    Args:
        df: 包含 close, open, high, low, volume 列的 DataFrame，按 date 升序排列

    Returns:
        同一 DataFrame 新增指标列
    """
    df = df.copy()
    close = df['close'].astype(float)
    volume = df['volume'].astype(float) if 'volume' in df.columns else None

    # --- 移动平均线 ---
    df['ma5'] = close.rolling(window=5, min_periods=1).mean()
    df['ma10'] = close.rolling(window=10, min_periods=1).mean()
    df['ma20'] = close.rolling(window=20, min_periods=1).mean()
    df['ma60'] = close.rolling(window=60, min_periods=1).mean()

    # --- RSI(14) ---
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=14, min_periods=1).mean()
    loss = (-delta.clip(upper=0)).rolling(window=14, min_periods=1).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = (100 - 100 / (1 + rs)).fillna(50)

    # --- MACD (12, 26, 9) ---
    ema12 = close.ewm(span=12, adjust=False, min_periods=1).mean()
    ema26 = close.ewm(span=26, adjust=False, min_periods=1).mean()
    dif = ema12 - ema26
    dea = dif.ewm(span=9, adjust=False, min_periods=1).mean()
    macd_bar = 2 * (dif - dea)
    df['macd_dif'] = dif
    df['macd_dea'] = dea
    df['macd_bar'] = macd_bar

    # --- 成交量均线 ---
    if volume is not None:
        df['volume_ma20'] = volume.rolling(window=20, min_periods=1).mean()

    # --- 涨跌幅 ---
    df['change_pct'] = close.pct_change() * 100

    return df


def trend_score(df: pd.DataFrame, lookback: int = 3) -> float:
    """
    趋势评分 0-40 分：
    - 均线多头排列（ma5>ma10>ma20）= 40
    - ma5 在 ma10/ma20 之上 = 25
    - 缠论/横盘 = 15
    - ma5 在 ma10/ma20 之下 = 5
    - 均线空头排列（ma5<ma10<ma20）= 0
    """
    if len(df) < lookback:
        return 15.0  # 数据不足给中性分

    row = df.iloc[-lookback] if lookback > 1 else df.iloc[-1]
    ma5: float = float(row.get('ma5', 0) or 0)
    ma10: float = float(row.get('ma10', 0) or 0)
    ma20: float = float(row.get('ma20', 0) or 0)
    close: float = float(row.get('close', 0) or 0)

    if ma5 <= 0 or ma10 <= 0 or ma20 <= 0 or close <= 0:
        return 15.0

    # 多头排列
    if ma5 > ma10 > ma20 and close > ma5:
        return 40.0
    # 空头排列
    if ma5 < ma10 < ma20 and close < ma5:
        return 0.0
    # 偏多
    if ma5 > ma10 > ma20:
        return 30.0
    if ma5 > ma10 and close > ma5:
        return 25.0
    if close > ma5:
        return 18.0
    if close < ma5:
        return 8.0
    return 15.0


def momentum_score(df: pd.DataFrame) -> float:
    """
    动量评分 0-30 分：
    - RSI(14) < 30（超卖）= 30
    - RSI(14) 30-40 = 22
    - RSI(14) 40-60 = 15
    - RSI(14) 60-70 = 8
    - RSI(14) > 70（超买）= 0
    """
    if len(df) < 14:
        return 15.0
    rsi = float(df.iloc[-1].get('rsi_14', 50) or 50)
    if rsi < 30:
        return 30.0
    elif rsi < 40:
        return 22.0
    elif rsi < 60:
        return 15.0
    elif rsi < 70:
        return 8.0
    else:
        return 0.0


def volume_score(df: pd.DataFrame) -> float:
    """
    量价评分 0-30 分：
    - 放量上涨（volume > ma20_vol AND close > open）= 30
    - 放量下跌（volume > ma20_vol AND close < open）= 0
    - 缩量上涨（温和）= 22
    - 平量整理 = 15
    """
    if len(df) < 20:
        return 15.0
    row = df.iloc[-1]
    vol = float(row.get('volume', 0) or 0)
    vol_ma20 = float(row.get('volume_ma20', 0) or 0)
    close = float(row.get('close', 0) or 0)
    open_ = float(row.get('open', close) or close)

    if vol_ma20 <= 0 or vol <= 0:
        return 15.0

    ratio = vol / vol_ma20
    price_up = close >= open_

    if ratio > 1.2:
        return 30.0 if price_up else 0.0
    elif ratio > 0.8:
        return 22.0 if price_up else 10.0
    else:
        return 18.0 if price_up else 12.0


def price_breakout(df: pd.DataFrame) -> bool:
    """价格是否突破 MA20"""
    if len(df) < 2:
        return False
    prev = df.iloc[-2]
    curr = df.iloc[-1]
    ma20_prev = float(prev.get('ma20', 0) or 0)
    ma20_curr = float(curr.get('ma20', 0) or 0)
    close_prev = float(prev.get('close', 0) or 0)
    close_curr = float(curr.get('close', 0) or 0)
    return close_prev < ma20_prev and close_curr > ma20_curr
