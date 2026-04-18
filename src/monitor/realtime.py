# 实时监控模块
"""
实时监控 NGA 帖子，有新内容时自动分析并推送
"""
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable
import threading
from dataclasses import dataclass

@dataclass
class MonitorConfig:
    """监控配置"""
    tid: str                          # 帖子ID
    check_interval: int = 300         # 检查间隔（秒），默认5分钟
    max_pages: int = 3                # 每次检查爬取页数
    emotion_threshold: float = 0.2    # 情绪变化阈值（20%）
    notify_on_change: bool = True     # 变化时通知

def clean_text(text: str) -> str:
    """清理文本"""
    # 去除HTML标签
    import re
    text = re.sub(r'<[^>]+>', '', text)
    # 去除特殊字符
    text = re.sub(r'[\n\r\t]', ' ', text)
    return text

def extract_stocks(text: str) -> List[Stock]:
    """
    从文本中提取股票
    
    Args:
        text: 原始文本
        
    Returns:
        股票列表
    """
    stocks = []
    
    # 1. 提取股票代码 (6位数字)
    code_pattern = r'(?<![\d])(6\d{5}|0\d{5}|3\d{5}|68\d{4})(?![\d])'
    codes = re.findall(code_pattern, text)
    
    for code in codes:
        market = "SH" if code.startswith('6') else "SZ"
        stocks.append(Stock(
            name=code,
            code=code,
            market=market
        ))
    
    # 2. 提取股票名称 (从常用股票字典)
    stock_dict = get_stock_dict()
    
    for name, info in stock_dict.items():
        # 匹配股票名称（确保是完整词）
        pattern = r'(?<![\u4e00-\u9fa5a-zA-Z])' + re.escape(name) + r'(?![\u4e00-\u9fa5a-zA-Z])'
        matches = re.findall(pattern, text)
        
        if matches:
            stocks.append(Stock(
                name=name,
                code=info['code'],
                market=info['market'],
                mention_count=len(matches)
            ))
    
    # 去重
    seen = set()
    unique_stocks = []
    for stock in stocks:
        key = stock.code
        if key not in seen:
            seen.add(key)
            unique_stocks.append(stock)
    
    return unique_stocks

def get_stock_dict() -> Dict[str, Dict]:
    """
    常用股票字典
    实际项目中可以从数据库或API获取
    """
    return {
        # 白酒
        "茅台": {"code": "600519", "market": "SH"},
        "五粮液": {"code": "000858", "market": "SZ"},
        "泸州老窖": {"code": "000568", "market": "SZ"},
        "洋河": {"code": "002304", "market": "SZ"},
        
        # 新能源
        "比亚迪": {"code": "002594", "market": "SZ"},
        "宁德时代": {"code": "300750", "market": "SZ"},
        "隆基": {"code": "601012", "market": "SH"},
        "通威": {"code": "600438", "market": "SH"},
        
        # 银行
        "招商银行": {"code": "600036", "market": "SH"},
        "平安银行": {"code": "000001", "market": "SZ"},
        
        # 科技
        "腾讯": {"code": "00700", "market": "HK"},
        "阿里巴巴": {"code": "09988", "market": "HK"},
        "美团": {"code": "03690", "market": "HK"},
        
        # 指数
        "上证": {"code": "000001", "market": "INDEX"},
        "沪深300": {"code": "000300", "market": "INDEX"},
        "创业板": {"code": "399006", "market": "INDEX"},
    }

def analyze_stock_mentions(posts: List[str]) -> List[Stock]:
    """
    分析帖子中股票提及情况
    
    Args:
        posts: 帖子内容列表
        
    Returns:
        按提及次数排序的股票列表
    """
    all_stocks = {}
    
    for post in posts:
        stocks = extract_stocks(post)
        for stock in stocks:
            code = stock.code
            if code in all_stocks:
                all_stocks[code].mention_count += stock.mention_count
            else:
                all_stocks[code] = stock
    
    # 按提及次数排序
    sorted_stocks = sorted(all_stocks.values(), key=lambda x: x.mention_count, reverse=True)
    
    return sorted_stocks

def main():
    """主函数"""
    render_header()
    render_sidebar()
    
    # 页面导航
    page = st.radio(
        "选择功能",
        ["🔍 帖子分析", "👁️ 实时监控", "📚 历史记录"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if "帖子分析" in page:
        render_analysis_page()
    elif "实时监控" in page:
        render_monitor_page()
    elif "历史记录" in page:
        render_history_page()

if __name__ == "__main__":
    main()
