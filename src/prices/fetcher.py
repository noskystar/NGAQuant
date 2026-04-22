"""
股票价格数据获取 - 通过 baostock（akshare 被服务器封锁时备用）
"""
import baostock as bs
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional
import logging
import time

logger = logging.getLogger(__name__)

_bs_logged_in = False


def _ensure_login():
    global _bs_logged_in
    if not _bs_logged_in:
        bs.login()
        _bs_logged_in = True


class PriceFetcher:
    """股票价格获取器（baostock 方案）"""

    @staticmethod
    def _to_float(val) -> Optional[float]:
        try:
            f = float(val)
            return f if f > 0 else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def get_realtime(code: str) -> Optional[Dict]:
        """
        获取单只股票最新行情
        baostock 无实时接口，用日线最后一条代替
        """
        try:
            _ensure_login()
            bs_code = f"sh.{code}" if code.startswith(('6', '5', '9')) else f"sz.{code}"
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume",
                start_date=(date.today() - timedelta(days=5)).strftime("%Y-%m-%d"),
                end_date=date.today().strftime("%Y-%m-%d"),
                frequency="d",
            )
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return None
            latest = rows[-1]
            prev_close = float(rows[-2][4]) if len(rows) > 1 else None
            curr_close = PriceFetcher._to_float(latest[4])
            change_pct = ((curr_close - prev_close) / prev_close * 100) if prev_close and curr_close else 0.0
            return {
                'code': code,
                'name': '',
                'price': curr_close,
                'change_pct': round(change_pct, 2),
                'volume': int(float(latest[5])) if latest[5] else 0,
                'high': PriceFetcher._to_float(latest[3]),
                'low': PriceFetcher._to_float(latest[2]),
                'open': PriceFetcher._to_float(latest[1]),
            }
        except Exception as e:
            logger.warning(f"获取 {code} 实时行情失败: {e}")
            return None

    @staticmethod
    def get_daily(
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> Optional[pd.DataFrame]:
        """
        获取日线数据（baostock）

        Args:
            code: 股票代码如 '600519'
            start_date: 'YYYY-MM-DD'
            end_date: 'YYYY-MM-DD'
            period: daily/weekly/monthly（baostock 只支持 d/w/m）
            adjust: 复权类型（baostock 支持 qfq/hfq/none）
        """
        try:
            _ensure_login()
            bs_code = f"sh.{code}" if code.startswith(('6', '5', '9')) else f"sz.{code}"
            if end_date is None:
                end_date = date.today().strftime("%Y-%m-%d")
            if start_date is None:
                start_date = (date.today() - timedelta(days=120)).strftime("%Y-%m-%d")

            freq_map = {"daily": "d", "weekly": "w", "monthly": "m"}
            freq = freq_map.get(period, "d")
            adjust_map = {"qfq": "2", "hfq": "1", "none": "3"}
            adjust_code = adjust_map.get(adjust, "2")

            # 基础字段（复权数据不支持 turnover/amount）
            fields = "date,open,high,low,close,volume"
            rs = bs.query_history_k_data_plus(
                bs_code,
                fields,
                start_date=start_date,
                end_date=end_date,
                frequency=freq,
                adjustflag=adjust_code,
            )

            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())

            if not rows:
                return None

            df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
            # 转换数值列
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            # 涨跌幅（百分比）
            df["change_pct"] = df["close"].pct_change() * 100

            df["date"] = pd.to_datetime(df["date"])
            df["code"] = code
            df = df.dropna(subset=["close"])
            return df
        except Exception as e:
            logger.warning(f"获取 {code} 日线数据失败: {e}")
            return None

    @staticmethod
    def get_index_daily(index_code: str = "000001") -> Optional[pd.DataFrame]:
        """获取指数日线（上证指数 sh.000001）"""
        try:
            _ensure_login()
            bs_code = f"sh.{index_code}"
            rs = bs.query_history_k_data_plus(
                bs_code,
                "date,open,high,low,close,volume",
                start_date=(date.today() - timedelta(days=120)).strftime("%Y-%m-%d"),
                end_date=date.today().strftime("%Y-%m-%d"),
                frequency="d",
            )
            rows = []
            while rs.error_code == "0" and rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return None
            df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["date"] = pd.to_datetime(df["date"])
            return df
        except Exception as e:
            logger.warning(f"获取指数 {index_code} 失败: {e}")
            return None

    @staticmethod
    def get_batch_realtime(codes: List[str]) -> Dict[str, Dict]:
        """批量获取实时行情"""
        results = {}
        for code in codes:
            data = PriceFetcher.get_realtime(code)
            if data:
                results[code] = data
            time.sleep(0.05)  # 避免请求过快
        return results
