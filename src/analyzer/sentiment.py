# 情感分析模块
"""
使用 LLM (Kimi) 分析 NGA 帖子情感倾向
"""
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import json

class SentimentType(Enum):
    """情感类型"""
    BULLISH = "看涨"      # 强烈看涨
    SLIGHTLY_BULLISH = "轻度看涨"
    NEUTRAL = "中性"
    SLIGHTLY_BEARISH = "轻度看跌"
    BEARISH = "看跌"      # 强烈看跌

@dataclass
class SentimentResult:
    """情感分析结果"""
    sentiment: SentimentType
    confidence: float  # 0-1
    reasoning: str
    mentioned_stocks: List[str]
    key_points: List[str]

class LLMClient:
    """Kimi API 客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("KIMI_API_KEY")
        self.base_url = "https://api.moonshot.cn/v1"
        
        try:
            import openai
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except ImportError:
            print("请先安装 openai: pip install openai")
            self.client = None
    
    def analyze_sentiment(self, text: str, context: Optional[str] = None) -> SentimentResult:
        """
        分析文本情感倾向
        
        Args:
            text: 帖子内容
            context: 上下文（前后文）
            
        Returns:
            情感分析结果
        """
        if not self.client:
            return SentimentResult(
                sentiment=SentimentType.NEUTRAL,
                confidence=0.0,
                reasoning="LLM 客户端未初始化",
                mentioned_stocks=[],
                key_points=[]
            )
        
        prompt = self._build_sentiment_prompt(text, context)
        
        try:
            response = self.client.chat.completions.create(
                model="kimi-latest",  # 或 kimi-k2-0711
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的股市情感分析专家。分析散户论坛帖子中的投资情绪和观点。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 低温度，更确定
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return self._parse_result(result)
            
        except Exception as e:
            print(f"LLM 分析失败: {e}")
            return SentimentResult(
                sentiment=SentimentType.NEUTRAL,
                confidence=0.0,
                reasoning=f"分析失败: {str(e)}",
                mentioned_stocks=[],
                key_points=[]
            )
    
    def _build_sentiment_prompt(self, text: str, context: Optional[str]) -> str:
        """构建情感分析提示"""
        prompt = f"""请分析以下 NGA 大时代板块帖子的投资情感倾向。

帖子内容：
{text}

{f"上下文：{context}" if context else ""}

请以 JSON 格式输出：
{{
    "sentiment": "看涨/轻度看涨/中性/轻度看跌/看跌",
    "confidence": 0.85,
    "reasoning": "分析理由...",
    "mentioned_stocks": ["茅台", "比亚迪"],
    "key_points": ["观点1", "观点2"],
    "market_emotion": "贪婪/恐惧/中性",
    "risk_level": "高/中/低"
}}

分析维度：
1. 整体看涨/看跌倾向
2. 情绪强度（confidence）
3. 提到的股票
4. 关键观点提取
5. 市场情绪（贪婪/恐惧）
6. 风险等级"""
        return prompt
    
    def _parse_result(self, result: Dict) -> SentimentResult:
        """解析 LLM 返回结果"""
        sentiment_map = {
            "看涨": SentimentType.BULLISH,
            "强烈看涨": SentimentType.BULLISH,
            "轻度看涨": SentimentType.SLIGHTLY_BULLISH,
            "中性": SentimentType.NEUTRAL,
            "轻度看跌": SentimentType.SLIGHTLY_BEARISH,
            "看跌": SentimentType.BEARISH,
            "强烈看跌": SentimentType.BEARISH,
        }
        
        sentiment_str = result.get("sentiment", "中性")
        sentiment = sentiment_map.get(sentiment_str, SentimentType.NEUTRAL)
        
        return SentimentResult(
            sentiment=sentiment,
            confidence=result.get("confidence", 0.5),
            reasoning=result.get("reasoning", ""),
            mentioned_stocks=result.get("mentioned_stocks", []),
            key_points=result.get("key_points", [])
        )
    
    def batch_analyze(self, posts: List[str]) -> List[SentimentResult]:
        """批量分析"""
        results = []
        for i, post in enumerate(posts):
            print(f"分析第 {i+1}/{len(posts)} 条帖子...")
            result = self.analyze_sentiment(post)
            results.append(result)
        return results


class SentimentAggregator:
    """情感聚合器 - 统计多个帖子的整体情绪"""
    
    @staticmethod
    def aggregate(results: List[SentimentResult]) -> Dict:
        """
        聚合多个情感分析结果
        
        Returns:
            统计报告
        """
        if not results:
            return {"error": "没有分析结果"}
        
        # 情感分布统计
        sentiment_counts = {
            SentimentType.BULLISH: 0,
            SentimentType.SLIGHTLY_BULLISH: 0,
            SentimentType.NEUTRAL: 0,
            SentimentType.SLIGHTLY_BEARISH: 0,
            SentimentType.BEARISH: 0,
        }
        
        for result in results:
            sentiment_counts[result.sentiment] += 1
        
        total = len(results)
        
        # 计算看涨/看跌比例
        bullish = sentiment_counts[SentimentType.BULLISH] + sentiment_counts[SentimentType.SLIGHTLY_BULLISH]
        bearish = sentiment_counts[SentimentType.BEARISH] + sentiment_counts[SentimentType.SLIGHTLY_BEARISH]
        neutral = sentiment_counts[SentimentType.NEUTRAL]
        
        # 市场情绪指数 (0-100, 50为中性)
        emotion_index = 50 + (bullish - bearish) / total * 50
        
        # 平均置信度
        avg_confidence = sum(r.confidence for r in results) / total
        
        # 收集所有提到的股票
        all_stocks = []
        for result in results:
            if result.mentioned_stocks:
                all_stocks.extend(result.mentioned_stocks)
        
        # 股票频率统计
        from collections import Counter
        stock_freq = Counter(all_stocks).most_common(10)
        
        return {
            "total_posts": total,
            "sentiment_distribution": {
                "strong_bullish": sentiment_counts[SentimentType.BULLISH],
                "slightly_bullish": sentiment_counts[SentimentType.SLIGHTLY_BULLISH],
                "neutral": neutral,
                "slightly_bearish": sentiment_counts[SentimentType.SLIGHTLY_BEARISH],
                "strong_bearish": sentiment_counts[SentimentType.BEARISH],
            },
            "bullish_ratio": bullish / total,
            "bearish_ratio": bearish / total,
            "neutral_ratio": neutral / total,
            "emotion_index": emotion_index,  # 0-100
            "avg_confidence": avg_confidence,
            "top_stocks": stock_freq,
            "market_emotion": "贪婪" if emotion_index > 70 else "恐惧" if emotion_index < 30 else "中性",
        }


# 测试
if __name__ == "__main__":
    # 测试情感分析
    client = LLMClient()
    
    test_text = """
    今天大盘太惨了，茅台跌停，我觉得可以抄底了！
    比亚迪最近不错，新能源车前景很好，建议买入。
    但是要注意风险，别满仓。
    """
    
    result = client.analyze_sentiment(test_text)
    
    print(f"情感: {result.sentiment.value}")
    print(f"置信度: {result.confidence}")
    print(f"理由: {result.reasoning}")
    print(f"提到的股票: {result.mentioned_stocks}")
