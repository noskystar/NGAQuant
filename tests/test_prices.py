import pytest
from src.prices.fetcher import PriceFetcher


class TestPriceFetcher:
    def test_get_batch_realtime_with_names(self):
        stocks = [
            {"name": "贵州茅台", "code": "600519"},
            {"name": "比亚迪", "code": "002594"},
        ]
        results = PriceFetcher.get_batch_realtime_with_names(stocks)
        assert len(results) <= len(stocks)
        for code, data in results.items():
            assert "name" in data
            assert "price" in data
            assert data["name"] != ""
