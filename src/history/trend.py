"""
情绪变化趋势分析
"""
from .manager import HistoryManager, AnalysisRecord


class EmotionTrend:
    """情绪趋势分析器"""

    @staticmethod
    def analyze(trend_data: dict) -> str:
        """生成趋势分析报告"""
        if "error" in trend_data:
            return f"❌ {trend_data['error']}"

        records = trend_data.get("records", [])
        if not records:
            return "暂无历史数据"

        lines = [f"📊 帖子 {trend_data['tid']} 情绪趋势（共 {trend_data['count']} 次分析）\n"]

        for rec in records:
            at = rec["analyzed_at"][:16].replace("T", " ")
            idx = rec["emotion_index"]
            label = rec["emotion_label"]
            vs = rec.get("vs_previous", {})
            direction = vs.get("direction", "")
            diff = vs.get("emotion_diff", 0)

            emoji = "🟢" if idx >= 65 else "🔴" if idx <= 35 else "🟡"
            diff_str = f" {direction}{abs(diff):.1f}" if diff else ""

            line = f"{emoji} {at} | 情绪指数 {idx:.1f}（{label}）{diff_str}"
            lines.append(line)

            if "stocks_changes" in rec:
                sc = rec["stocks_changes"]
                if sc["new"]:
                    lines.append(f"   🆕 新热门：{' '.join(sc['new'])}")
                if sc["gone"]:
                    lines.append(f"   ➖ 退出热门：{' '.join(sc['gone'])}")

        return "\n".join(lines)
