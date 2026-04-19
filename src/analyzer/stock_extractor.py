"""
股票提取器 - 从文本中提取股票名称和代码
"""
import re
from typing import List, Dict, Tuple, Set, Optional
from dataclasses import dataclass
from functools import lru_cache

@dataclass
class Stock:
    """股票信息"""
    name: str
    code: str
    market: str  # SH/SZ/HK/US/INDEX
    mention_count: int = 1
    
    def __hash__(self):
        return hash(self.code)
    
    def __eq__(self, other):
        if isinstance(other, Stock):
            return self.code == other.code
        return False


# ==========================================
# 股票字典 - 支持A股、港股、美股、指数
# ==========================================

A_SHARES = {
    # 白酒
    "贵州茅台": {"code": "600519", "market": "SH", "aliases": ["茅台", "贵州茅台", "600519"]},
    "五粮液": {"code": "000858", "market": "SZ", "aliases": ["五粮液", "000858"]},
    "泸州老窖": {"code": "000568", "market": "SZ", "aliases": ["泸州老窖", "老窖", "000568"]},
    "洋河股份": {"code": "002304", "market": "SZ", "aliases": ["洋河", "洋河股份", "002304"]},
    "山西汾酒": {"code": "600809", "market": "SH", "aliases": ["汾酒", "山西汾酒", "600809"]},
    "古井贡酒": {"code": "000596", "market": "SZ", "aliases": ["古井贡", "古井贡酒", "000596"]},
    "今世缘": {"code": "603369", "market": "SH", "aliases": ["今世缘", "603369"]},
    
    # 新能源
    "比亚迪": {"code": "002594", "market": "SZ", "aliases": ["比亚迪", "002594", "BYD"]},
    "宁德时代": {"code": "300750", "market": "SZ", "aliases": ["宁德", "宁德时代", "300750", "CATL"]},
    "隆基绿能": {"code": "601012", "market": "SH", "aliases": ["隆基", "隆基绿能", "601012"]},
    "通威股份": {"code": "600438", "market": "SH", "aliases": ["通威", "通威股份", "600438"]},
    "阳光电源": {"code": "300274", "market": "SZ", "aliases": ["阳光电源", "300274"]},
    "晶澳科技": {"code": "002459", "market": "SZ", "aliases": ["晶澳", "晶澳科技", "002459"]},
    "天合光能": {"code": "688599", "market": "SH", "aliases": ["天合光能", "688599"]},
    "晶科能源": {"code": "688223", "market": "SH", "aliases": ["晶科", "晶科能源", "688223"]},
    "亿纬锂能": {"code": "300014", "market": "SZ", "aliases": ["亿纬锂能", "300014"]},
    "天赐材料": {"code": "002709", "market": "SZ", "aliases": ["天赐材料", "002709"]},
    "恩捷股份": {"code": "002812", "market": "SZ", "aliases": ["恩捷", "恩捷股份", "002812"]},
    
    # 银行
    "招商银行": {"code": "600036", "market": "SH", "aliases": ["招行", "招商银行", "600036"]},
    "平安银行": {"code": "000001", "market": "SZ", "aliases": ["平安银行", "000001"]},
    "兴业银行": {"code": "601166", "market": "SH", "aliases": ["兴业", "兴业银行", "601166"]},
    "宁波银行": {"code": "002142", "market": "SZ", "aliases": ["宁波银行", "002142"]},
    "邮储银行": {"code": "601658", "market": "SH", "aliases": ["邮储", "邮储银行", "601658"]},
    "工商银行": {"code": "601398", "market": "SH", "aliases": ["工行", "工商银行", "601398"]},
    "建设银行": {"code": "601939", "market": "SH", "aliases": ["建行", "建设银行", "601939"]},
    "农业银行": {"code": "601288", "market": "SH", "aliases": ["农行", "农业银行", "601288"]},
    
    # 券商
    "中信证券": {"code": "600030", "market": "SH", "aliases": ["中信", "中信证券", "600030"]},
    "东方财富": {"code": "300059", "market": "SZ", "aliases": ["东财", "东方财富", "300059"]},
    "华泰证券": {"code": "601688", "market": "SH", "aliases": ["华泰", "华泰证券", "601688"]},
    "国泰君安": {"code": "601211", "market": "SH", "aliases": ["国泰", "国泰君安", "601211"]},
    
    # 科技/半导体
    "中芯国际": {"code": "688981", "market": "SH", "aliases": ["中芯", "中芯国际", "688981", "SMIC"]},
    "海光信息": {"code": "688041", "market": "SH", "aliases": ["海光", "海光信息", "688041"]},
    "北方华创": {"code": "002371", "market": "SZ", "aliases": ["北方华创", "002371"]},
    "韦尔股份": {"code": "603501", "market": "SH", "aliases": ["韦尔", "韦尔股份", "603501"]},
    "兆易创新": {"code": "603986", "market": "SH", "aliases": ["兆易创新", "603986"]},
    "紫光国微": {"code": "002049", "market": "SZ", "aliases": ["紫光国微", "002049"]},
    "科大讯飞": {"code": "002230", "market": "SZ", "aliases": ["讯飞", "科大讯飞", "002230"]},
    "金山办公": {"code": "688111", "market": "SH", "aliases": ["金山", "金山办公", "688111"]},
    "海康威视": {"code": "002415", "market": "SZ", "aliases": ["海康", "海康威视", "002415"]},
    "立讯精密": {"code": "002475", "market": "SZ", "aliases": ["立讯", "立讯精密", "002475"]},
    "京东方A": {"code": "000725", "market": "SZ", "aliases": ["京东方", "京东方A", "000725", "BOE"]},
    "TCL科技": {"code": "000100", "market": "SZ", "aliases": ["TCL", "TCL科技", "000100"]},
    
    # 医药
    "恒瑞医药": {"code": "600276", "market": "SH", "aliases": ["恒瑞", "恒瑞医药", "600276"]},
    "迈瑞医疗": {"code": "300760", "market": "SZ", "aliases": ["迈瑞", "迈瑞医疗", "300760"]},
    "药明康德": {"code": "603259", "market": "SH", "aliases": ["药明", "药明康德", "603259"]},
    "爱尔眼科": {"code": "300015", "market": "SZ", "aliases": ["爱尔", "爱尔眼科", "300015"]},
    "片仔癀": {"code": "600436", "market": "SH", "aliases": ["片仔癀", "600436"]},
    "智飞生物": {"code": "300122", "market": "SZ", "aliases": ["智飞", "智飞生物", "300122"]},
    
    # 消费
    "美的集团": {"code": "000333", "market": "SZ", "aliases": ["美的", "美的集团", "000333"]},
    "格力电器": {"code": "000651", "market": "SZ", "aliases": ["格力", "格力电器", "000651"]},
    "海尔智家": {"code": "600690", "market": "SH", "aliases": ["海尔", "海尔智家", "600690"]},
    "伊利股份": {"code": "600887", "market": "SH", "aliases": ["伊利", "伊利股份", "600887"]},
    "海天味业": {"code": "603288", "market": "SH", "aliases": ["海天", "海天味业", "603288"]},
    "中国中免": {"code": "601888", "market": "SH", "aliases": ["中免", "中国中免", "601888"]},
    "牧原股份": {"code": "002714", "market": "SZ", "aliases": ["牧原", "牧原股份", "002714"]},
    
    # 汽车
    "长城汽车": {"code": "601633", "market": "SH", "aliases": ["长城", "长城汽车", "601633"]},
    "长安汽车": {"code": "000625", "market": "SZ", "aliases": ["长安", "长安汽车", "000625"]},
    "上汽集团": {"code": "600104", "market": "SH", "aliases": ["上汽", "上汽集团", "600104"]},
    "福耀玻璃": {"code": "600660", "market": "SH", "aliases": ["福耀", "福耀玻璃", "600660"]},
    "赛力斯": {"code": "601127", "market": "SH", "aliases": ["赛力斯", "601127", "小康"]},
    "理想汽车": {"code": "LI", "market": "US", "aliases": ["理想", "理想汽车", "LI"]},
    "蔚来": {"code": "NIO", "market": "US", "aliases": ["蔚来", "NIO"]},
    "小鹏汽车": {"code": "XPEV", "market": "US", "aliases": ["小鹏", "小鹏汽车", "XPEV"]},
    
    # 能源/电力
    "长江电力": {"code": "600900", "market": "SH", "aliases": ["长电", "长江电力", "600900"]},
    "中国神华": {"code": "601088", "market": "SH", "aliases": ["神华", "中国神华", "601088"]},
    "陕西煤业": {"code": "601225", "market": "SH", "aliases": ["陕煤", "陕西煤业", "601225"]},
    "华能水电": {"code": "600025", "market": "SH", "aliases": ["华能水电", "600025"]},
    "中国核电": {"code": "601985", "market": "SH", "aliases": ["核电", "中国核电", "601985"]},
    "三峡能源": {"code": "600905", "market": "SH", "aliases": ["三峡", "三峡能源", "600905"]},
    "中国石油": {"code": "601857", "market": "SH", "aliases": ["中石油", "中国石油", "601857", "PetroChina"]},
    "中国海油": {"code": "600938", "market": "SH", "aliases": ["中海油", "中国海油", "600938", "CNOOC"]},
    
    # 中字头/国企
    "中国移动": {"code": "600941", "market": "SH", "aliases": ["移动", "中国移动", "600941"]},
    "中国电信": {"code": "601728", "market": "SH", "aliases": ["电信", "中国电信", "601728"]},
    "中国联通": {"code": "600050", "market": "SH", "aliases": ["联通", "中国联通", "600050"]},
    "中国船舶": {"code": "600150", "market": "SH", "aliases": ["船舶", "中国船舶", "600150"]},
    "中国建筑": {"code": "601668", "market": "SH", "aliases": ["中建", "中国建筑", "601668"]},
    "中国中铁": {"code": "601390", "market": "SH", "aliases": ["中铁", "中国中铁", "601390"]},
    "中国铁建": {"code": "601186", "market": "SH", "aliases": ["铁建", "中国铁建", "601186"]},
    "中国交建": {"code": "601800", "market": "SH", "aliases": ["中交", "中国交建", "601800"]},
}

HK_SHARES = {
    "腾讯控股": {"code": "00700", "market": "HK", "aliases": ["腾讯", "00700", "Tencent"]},
    "阿里巴巴": {"code": "09988", "market": "HK", "aliases": ["阿里", "阿里巴巴", "09988", "BABA", "Alibaba"]},
    "美团": {"code": "03690", "market": "HK", "aliases": ["美团", "03690", "Meituan"]},
    "京东": {"code": "09618", "market": "HK", "aliases": ["京东", "09618", "JD", "京东集团"]},
    "小米集团": {"code": "01810", "market": "HK", "aliases": ["小米", "01810", "Xiaomi", "雷军"]},
    "比亚迪股份": {"code": "01211", "market": "HK", "aliases": ["比亚迪H", "01211"]},
    "网易": {"code": "09999", "market": "HK", "aliases": ["网易", "09999", "NetEase"]},
    "百度": {"code": "09888", "market": "HK", "aliases": ["百度", "09888", "Baidu"]},
    "快手": {"code": "01024", "market": "HK", "aliases": ["快手", "01024", "Kuaishou"]},
    "港交所": {"code": "00388", "market": "HK", "aliases": ["港交所", "00388", "HKEX"]},
    "中芯国际H": {"code": "00981", "market": "HK", "aliases": ["中芯H", "00981", "SMIC H"]},
    "药明生物": {"code": "02269", "market": "HK", "aliases": ["药明生物", "02269", "WuXi Biologics"]},
}

US_STOCKS = {
    "苹果": {"code": "AAPL", "market": "US", "aliases": ["苹果", "AAPL", "Apple"]},
    "微软": {"code": "MSFT", "market": "US", "aliases": ["微软", "MSFT", "Microsoft"]},
    "谷歌": {"code": "GOOGL", "market": "US", "aliases": ["谷歌", "GOOGL", "Google", "Alphabet"]},
    "亚马逊": {"code": "AMZN", "market": "US", "aliases": ["亚马逊", "AMZN", "Amazon"]},
    "特斯拉": {"code": "TSLA", "market": "US", "aliases": ["特斯拉", "TSLA", "Tesla"]},
    "英伟达": {"code": "NVDA", "market": "US", "aliases": ["英伟达", "NVDA", "NVIDIA", "nvdia"]},
    "Meta": {"code": "META", "market": "US", "aliases": ["Meta", "Facebook", "脸书"]},
    "台积电": {"code": "TSM", "market": "US", "aliases": ["台积电", "TSM", "TSMC"]},
    "AMD": {"code": "AMD", "market": "US", "aliases": ["AMD", "超威"]},
    "英特尔": {"code": "INTC", "market": "US", "aliases": ["英特尔", "INTC", "Intel"]},
    "奈飞": {"code": "NFLX", "market": "US", "aliases": ["奈飞", "NFLX", "Netflix", "网飞"]},
    "博通": {"code": "AVGO", "market": "US", "aliases": ["博通", "AVGO", "Broadcom"]},
}

INDEXES = {
    "上证指数": {"code": "000001", "market": "INDEX", "aliases": ["上证", "上证指数", "000001", "沪指", "大盘"]},
    "深证成指": {"code": "399001", "market": "INDEX", "aliases": ["深证", "深证成指", "399001", "深成指"]},
    "创业板指": {"code": "399006", "market": "INDEX", "aliases": ["创业板", "创业板指", "399006", "创业版"]},
    "科创50": {"code": "000688", "market": "INDEX", "aliases": ["科创", "科创50", "000688", "科创板"]},
    "沪深300": {"code": "000300", "market": "INDEX", "aliases": ["沪深300", "000300", "hs300"]},
    "上证50": {"code": "000016", "market": "INDEX", "aliases": ["上证50", "000016"]},
    "中证500": {"code": "000905", "market": "INDEX", "aliases": ["中证500", "000905"]},
    "中证1000": {"code": "000852", "market": "INDEX", "aliases": ["中证1000", "000852"]},
    "恒生指数": {"code": "HSI", "market": "INDEX", "aliases": ["恒指", "恒生", "HSI", "HangSeng"]},
    "纳斯达克": {"code": "IXIC", "market": "INDEX", "aliases": ["纳指", "纳斯达克", "IXIC", "Nasdaq"]},
    "标普500": {"code": "SPX", "market": "INDEX", "aliases": ["标普", "标普500", "SPX", "S&P500"]},
    "道琼斯": {"code": "DJI", "market": "INDEX", "aliases": ["道指", "道琼斯", "DJI", "DowJones"]},
}

# 合并所有股票
ALL_STOCKS = {**A_SHARES, **HK_SHARES, **US_STOCKS, **INDEXES}


def get_stock_dict() -> Dict[str, Dict]:
    """
    获取完整股票字典
    
    Returns:
        股票字典，包含所有A股、港股、美股和指数
    """
    return ALL_STOCKS.copy()


def get_stock_by_alias(alias: str) -> Optional[Stock]:
    """
    通过别名查找股票
    
    Args:
        alias: 股票别名（名称、代码或别名）
        
    Returns:
        找到的股票信息，找不到返回None
    """
    alias = alias.strip()
    
    # 直接匹配代码
    for name, info in ALL_STOCKS.items():
        if info['code'] == alias:
            return Stock(name=name, code=info['code'], market=info['market'])
        # 检查别名
        if alias in info.get('aliases', []):
            return Stock(name=name, code=info['code'], market=info['market'])
    
    return None


def clean_text(text: str) -> str:
    """清理文本"""
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去除特殊字符，保留中文、英文、数字
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\.\s]', ' ', text)
    # 合并多余空格
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_stock_codes(text: str) -> List[Stock]:
    """
    从文本中提取6位数字股票代码
    
    Args:
        text: 原始文本
        
    Returns:
        股票列表
    """
    stocks = []
    
    # 提取A股代码 (6位数字)
    # 沪市：600/601/603/688开头
    # 深市：000/001/002/300开头
    code_pattern = r'(?<![\d])(600\d{3}|601\d{3}|603\d{3}|605\d{3}|688\d{3}|000\d{3}|001\d{3}|002\d{3}|003\d{3}|300\d{3}|301\d{3})(?![\d])'
    codes = re.findall(code_pattern, text)
    
    for code in codes:
        # 判断市场
        if code.startswith('6') or code.startswith('688'):
            market = "SH"
        else:
            market = "SZ"
        
        # 尝试查找股票名称
        name = code  # 默认使用代码作为名称
        for stock_name, info in A_SHARES.items():
            if info['code'] == code:
                name = stock_name
                break
        
        stocks.append(Stock(name=name, code=code, market=market))
    
    return stocks


def extract_stock_names(text: str) -> List[Stock]:
    """
    从文本中提取股票名称
    
    Args:
        text: 原始文本
        
    Returns:
        股票列表
    """
    stocks = []
    
    # 清理文本
    cleaned = clean_text(text)
    
    for name, info in ALL_STOCKS.items():
        aliases = info.get('aliases', [])
        mention_count = 0
        
        for alias in aliases:
            # 使用词边界匹配
            pattern = r'(?<![\u4e00-\u9fa5a-zA-Z])' + re.escape(alias) + r'(?![\u4e00-\u9fa5a-zA-Z0-9])'
            matches = re.findall(pattern, cleaned, re.IGNORECASE)
            mention_count += len(matches)
        
        if mention_count > 0:
            stocks.append(Stock(
                name=name,
                code=info['code'],
                market=info['market'],
                mention_count=mention_count
            ))
    
    return stocks


def extract_stocks(text: str) -> List[Stock]:
    """
    从文本中提取所有股票信息（代码+名称）
    
    Args:
        text: 原始文本
        
    Returns:
        去重后的股票列表
    """
    # 合并两种提取方式的结果
    code_stocks = extract_stock_codes(text)
    name_stocks = extract_stock_names(text)
    
    # 使用字典去重（以代码为key）
    stock_dict = {}
    
    for stock in code_stocks + name_stocks:
        code = stock.code
        if code in stock_dict:
            # 合并提及次数
            stock_dict[code].mention_count += stock.mention_count
        else:
            stock_dict[code] = stock
    
    return list(stock_dict.values())


def analyze_stock_mentions(posts: List[str]) -> List[Stock]:
    """
    分析帖子中股票提及情况
    
    Args:
        posts: 帖子内容列表
        
    Returns:
        按提及次数排序的股票列表
    """
    all_stocks: Dict[str, Stock] = {}
    
    for post in posts:
        stocks = extract_stocks(post)
        for stock in stocks:
            code = stock.code
            if code in all_stocks:
                all_stocks[code].mention_count += stock.mention_count
            else:
                all_stocks[code] = stock
    
    # 按提及次数排序
    sorted_stocks = sorted(
        all_stocks.values(), 
        key=lambda x: x.mention_count, 
        reverse=True
    )
    
    return sorted_stocks


# 测试
if __name__ == "__main__":
    test_cases = [
        "今天茅台又跌了，我觉得600519可以抄底了。比亚迪最近不错，002594可以关注。",
        "宁德时代300750也有机会，新能源看好隆基601012和阳光电源",
        "纳指科技股大涨，AAPL和NVDA创新高，特斯拉TSLA回调",
        "腾讯00700和阿里09988港股反弹，小米01810也不错",
        "上证指数和创业板指都涨了，沪深300 hs300看好",
    ]
    
    for i, text in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {text[:50]}...")
        stocks = extract_stocks(text)
        print(f"提取到 {len(stocks)} 只股票:")
        for stock in stocks:
            print(f"  - {stock.name} ({stock.code}.{stock.market}) x{stock.mention_count}")
