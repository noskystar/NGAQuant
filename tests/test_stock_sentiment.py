# 单元测试 - 股票级情感分析
import pytest
from src.analyzer.sentiment import StockSentimentAnalyzer, StockSentiment
from src.analyzer.stock_extractor import StockExtractor

class TestStockSentimentAnalyzer:
    """测试股票级情感分析"""

    def test_get_context_window(self):
        """测试上下文滑窗提取"""
        extractor = StockExtractor(use_llm=False)
        analyzer = StockSentimentAnalyzer(extractor, None)

        text = "今天大盘很好。宁德时代涨疯了，新能源板块爆发。但是茅台在跌。"
        context = analyzer._get_context(text, "宁德时代", window=10)

        assert "宁德时代" in context
        assert "涨疯了" in context
        assert "茅台" not in context  # 滑窗外

    def test_get_context_multiple_mentions(self):
        """测试同一股票多处提及"""
        extractor = StockExtractor(use_llm=False)
        analyzer = StockSentimentAnalyzer(extractor, None)

        text = "宁德时代好。宁德时代真的好。"
        contexts = analyzer._get_all_contexts(text, "宁德时代", window=10)
        assert len(contexts) == 2

    def test_analyze_context_bullish(self):
        extractor = StockExtractor(use_llm=False)
        analyzer = StockSentimentAnalyzer(extractor, None)
        context = "宁德时代涨疯了，强烈看好，买入机会"
        result = analyzer._analyze_context(context)
        assert result["sentiment"] in ["bullish", "slightly_bullish"]
        assert result["score"] > 0

    def test_analyze_context_bearish(self):
        extractor = StockExtractor(use_llm=False)
        analyzer = StockSentimentAnalyzer(extractor, None)
        context = "宁德时代跌停了，快跑，出货"
        result = analyzer._analyze_context(context)
        assert result["sentiment"] in ["bearish", "slightly_bearish"]
        assert result["score"] < 0

    def test_analyze_context_neutral(self):
        extractor = StockExtractor(use_llm=False)
        analyzer = StockSentimentAnalyzer(extractor, None)
        context = "宁德时代今天成交量100亿"
        result = analyzer._analyze_context(context)
        assert result["sentiment"] == "neutral"