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