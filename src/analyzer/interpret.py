"""
通俗化信号解读 - 把冰冷的数据转化成散户能理解的语言
"""


class SignalInterpreter:
    """信号解读器"""

    @staticmethod
    def emotion_label(emotion_index: float) -> tuple:
        """
        把情绪指数转化为通俗语言
        Returns: (emoji, label, description)
        """
        if emotion_index >= 75:
            return "🔴", "极度贪婪", "市场情绪过热，很多人急着冲进去，这时候要小心！"
        elif emotion_index >= 60:
            return "🟡", "偏贪婪", "情绪偏暖，但还没过热，可以谨慎乐观"
        elif emotion_index >= 40:
            return "🟢", "中性", "情绪正常，没有明显的贪婪或恐惧，适合观望"
        elif emotion_index >= 25:
            return "🔵", "偏恐惧", "情绪偏冷，市场低迷，可能蕴藏着机会"
        else:
            return "🟣", "极度恐惧", "市场情绪到了冰点，往往是布局的好时机！"

    @staticmethod
    def signal_label(signal_type: str) -> tuple:
        """信号类型通俗化"""
        labels = {
            "BUY": ("🟢", "建议买入", "根据当前情绪和技术分析，系统认为可以关注"),
            "SELL": ("🔴", "建议回避", "市场情绪过热或技术面走弱，建议谨慎"),
            "ACCUMULATE": ("🟡", "可以布局", "中期趋势向好，可以考虑分批布局"),
            "REDUCE": ("⚠️", "考虑减仓", "中期风险增大，建议降低仓位"),
            "HOLD": ("⬜", "继续观望", "信号不明确，建议等待更好的时机"),
        }
        return labels.get(signal_type, ("❓", "未知信号", ""))

    @staticmethod
    def strength_label(strength: str) -> str:
        """信号强度通俗化"""
        labels = {
            "STRONG": "⭐⭐⭐ 强烈信号",
            "MODERATE": "⭐⭐ 中等信号",
            "WEAK": "⭐ 轻信号（仅观察）",
        }
        return labels.get(strength, strength)

    @staticmethod
    def advice_text(emotion_index: float, signal_type: str, composite_score: float) -> str:
        """
        生成通俗投资建议
        """
        emoji, emotion_desc, emotion_tip = SignalInterpreter.emotion_label(emotion_index)
        sig_emoji, sig_desc, sig_tip = SignalInterpreter.signal_label(signal_type)

        # 综合建议
        if signal_type in ("BUY", "ACCUMULATE"):
            if emotion_index < 40:
                tip = "情绪冰点 + 买入信号，是比较好的布局时机，但要注意仓位管理！"
            elif emotion_index < 60:
                tip = "情绪中性，可以谨慎参与，设置好止损位。"
            else:
                tip = "虽然有买入信号，但情绪已经偏暖，追高有风险！"
        elif signal_type in ("SELL", "REDUCE"):
            tip = "建议减仓或观望，等情绪回归中性再考虑进场。"
        else:
            tip = "建议继续观望，等待更明确的信号。"

        return f"{emotion_tip}\n{sig_tip}\n\n💡 {tip}"

    @staticmethod
    def kpi_card(emotion_index: float) -> dict:
        """
        生成仪表盘 KPI 卡片数据
        """
        emoji, label, desc = SignalInterpreter.emotion_label(emotion_index)

        # 温度计比喻
        temp = int(emotion_index)  # 0-100
        if temp >= 80:
            meter = "🔥 烫手"
            meter_color = "red"
        elif temp >= 60:
            meter = "☀️ 温暖"
            meter_color = "orange"
        elif temp >= 40:
            meter = "🌤️ 舒适"
            meter_color = "green"
        elif temp >= 20:
            meter = "🌧️ 偏冷"
            meter_color = "blue"
        else:
            meter = "❄️ 冰点"
            meter_color = "darkblue"

        return {
            "emotion_emoji": emoji,
            "emotion_label": label,
            "emotion_desc": desc,
            "emotion_index": emotion_index,
            "temperature": temp,
            "temperature_label": meter,
            "temperature_color": meter_color,
        }
