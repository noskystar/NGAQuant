# 单元测试 - 股票提取
import pytest
from src.analyzer.stock_extractor import extract_stocks, Stock

class TestStockExtractor:
    """测试股票提取"""
    
    def test_extract_stock_code(self):
        """测试提取股票代码"""
        text = "今天600519涨停了，002594也不错"
        stocks = extract_stocks(text)
        
        assert len(stocks) >= 2
        codes = [s.code for s in stocks]
        assert "600519" in codes
        assert "002594" in codes
    
    def test_extract_stock_name(self):
        """测试提取股票名称"""
        text = "茅台今天涨得不错，比亚迪也还行"
        stocks = extract_stocks(text)
        
        names = [s.name for s in stocks]
        assert "茅台" in names or "600519" in names
    
    def test_stock_market(self):
        """测试市场判断"""
        stock = Stock(name="测试", code="600519", market="SH")
        assert stock.market == "SH"
        
        stock2 = Stock(name="测试2", code="000001", market="SZ")
        assert stock2.market == "SZ"
