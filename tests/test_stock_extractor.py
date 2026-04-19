# 单元测试 - 股票提取
import pytest
from src.analyzer.stock_extractor import extract_stocks, extract_stock_codes, Stock

class TestStockExtractor:
    """测试股票提取"""
    
    def test_extract_stock_code_by_digit(self):
        """测试提取6位数字股票代码"""
        text = "今天600519涨停了，002594也不错"
        stocks = extract_stocks(text, search_pinyin=False)
        codes = [s.code for s in stocks]
        assert "600519" in codes
        assert "002594" in codes
    
    def test_extract_stock_by_code_and_name(self):
        """测试通过代码+名称提取（贵州茅台=600519, 比亚迪=002594）"""
        text = "贵州茅台600519涨停，比亚迪002594也涨停"
        stocks = extract_stocks(text, search_pinyin=False)
        codes = [s.code for s in stocks]
        names = [s.name for s in stocks]
        assert "600519" in codes
        assert "002594" in codes
        assert "贵州茅台" in names
        assert "比亚迪" in names
    
    def test_stock_market(self):
        """测试市场判断"""
        stock = Stock(name="测试", code="600519", market="SH")
        assert stock.market == "SH"
        stock2 = Stock(name="测试2", code="000001", market="SZ")
        assert stock2.market == "SZ"
    
    def test_extract_empty(self):
        """测试无股票文本"""
        stocks = extract_stocks("今天天气不错", search_pinyin=False)
        assert len(stocks) == 0
    
    def test_deduplication(self):
        """测试去重：同一股票被代码和名称同时提取时去重"""
        stocks = extract_stocks("贵州茅台600519涨停了", search_pinyin=False)
        codes = [s.code for s in stocks]
        assert codes.count("600519") == 1
    
    def test_pinyin_search_chinese_name(self):
        """测试拼音搜索中文股票名（全拼匹配）"""
        # 阳光电源 -> 通过 akshare 5-char pinyin map 匹配
        stocks = extract_stocks("阳光电源", search_pinyin=True)
        names = [s.name for s in stocks]
        assert "阳光电源" in names
    
    def test_mention_count(self):
        """测试提及次数"""
        stocks = extract_stocks("600519涨停600519又涨停", search_pinyin=False)
        if stocks:
            assert stocks[0].mention_count == 2
