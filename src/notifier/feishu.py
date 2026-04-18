# 飞书机器人推送模块
"""
飞书群机器人推送
"""
import requests
import json
from datetime import datetime
from typing import Optional, Dict

class FeishuNotifier:
    """飞书机器人通知器"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_text(self, text: str) -> bool:
        """发送纯文本消息"""
        data = {
            "msg_type": "text",
            "content": {
                "text": text
            }
        }
        return self._send(data)
    
    def send_markdown(self, title: str, content: str) -> bool:
        """发送 Markdown 消息"""
        data = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": content
                        }
                    }
                ]
            }
        }
        return self._send(data)
    
    def send_sentiment_report(
        self,
        tid: str,
        emotion_index: float,
        market_emotion: str,
        top_stocks: list,
        recommendation: str
    ) -> bool:
        """发送情绪分析报告"""
        # 根据情绪选择颜色
        if emotion_index > 70:
            color = "red"  # 贪婪
            emoji = "🔴"
        elif emotion_index < 30:
            color = "green"  # 恐惧
            emoji = "🟢"
        else:
            color = "blue"  # 中性
            emoji = "🟡"
        
        # 构建股票列表
        stock_text = "\n".join([f"• {name}: {count}次提及" for name, count in top_stocks[:5]])
        
        content = f"""## 📊 NGAQuant 情绪分析

**帖子 ID**: {tid}
**分析时间**: {datetime.now().strftime("%Y-%m-%d %H:%M")}

### 📈 市场情绪指数: {emotion_index:.1f}/100

**整体情绪**: {emoji} {market_emotion}

### 🔥 热门股票
{stock_text}

### 💡 投资建议
{recommendation}

---
*数据来源: NGA大时代板块 | AI智能分析*
"""
        
        return self.send_markdown("📈 NGAQuant 情绪分析报告", content)
    
    def send_alert(self, title: str, message: str) -> bool:
        """发送告警消息"""
        data = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"⚠️ {title}"
                    },
                    "template": "red"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": message
                        }
                    }
                ]
            }
        }
        return self._send(data)
    
    def _send(self, data: Dict) -> bool:
        """发送请求"""
        try:
            response = requests.post(
                self.webhook_url,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    return True
                else:
                    print(f"飞书推送失败: {result.get('msg')}")
                    return False
            else:
                print(f"飞书推送失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"飞书推送异常: {e}")
            return False


# 测试
if __name__ == "__main__":
    import os
    
    webhook = os.getenv("FEISHU_WEBHOOK")
    if webhook:
        notifier = FeishuNotifier(webhook)
        
        # 测试发送报告
        notifier.send_sentiment_report(
            tid="12345678",
            emotion_index=75.5,
            market_emotion="贪婪",
            top_stocks=[("茅台", 25), ("比亚迪", 18), ("宁德时代", 15)],
            recommendation="市场情绪过热，建议谨慎"
        )
    else:
        print("请设置 FEISHU_WEBHOOK 环境变量")
