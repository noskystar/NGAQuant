"""
NGAQuant Web Dashboard v3
两栏布局 - 帖子列表 + 分析结果区
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.board import BoardCrawler
from src.crawler.nga_client import NGACrawler
from src.analyzer.sentiment import LLMClient, SentimentAggregator, StockSentimentAnalyzer
from src.analyzer.stock_extractor import analyze_stock_mentions, StockExtractor
from src.analyzer.interpret import SignalInterpreter
from src.prices.fetcher import PriceFetcher
from src.config import config

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="NGAQuant - 散户情绪选股",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== 自定义样式 ====================
st.markdown("""
<style>
.stTitle {text-align: center; color: #1f77b4;}
.stMetric {background: #f0f2f6; border-radius: 10px; padding: 15px;}
.hot-post {background: #f8f9fa; border-radius: 8px; padding: 10px; margin: 5px 0; cursor: pointer;}
.hot-post:hover {background: #e3f2fd;}
.signal-card {background: #e8f5e9; border-radius: 12px; padding: 15px; margin: 8px 0;}
.warning-card {background: #ffebee; border-radius: 12px; padding: 15px; margin: 8px 0;}
.neutral-card {background: #f5f5f5; border-radius: 12px; padding: 15px; margin: 8px 0;}
.stock-card {border: 2px solid #e0e0e0; border-radius: 12px; padding: 12px; margin: 6px 0;}
.stock-card.bullish {border-color: #4caf50;}
.stock-card.bearish {border-color: #f44336;}
.stock-card.neutral {border-color: #9e9e9e;}
</style>
""", unsafe_allow_html=True)

# ==================== 初始化 ====================
if 'board_crawler' not in st.session_state:
    st.session_state.board_crawler = BoardCrawler()
if 'nga_crawler' not in st.session_state:
    st.session_state.nga_crawler = NGACrawler(cookie=config.nga.cookie)
if 'llm_client' not in st.session_state:
    st.session_state.llm_client = LLMClient(api_key=config.minimax.api_key)
if 'stock_extractor' not in st.session_state:
    st.session_state.stock_extractor = StockExtractor(use_llm=False)
if 'stock_sentiment_analyzer' not in st.session_state:
    st.session_state.stock_sentiment_analyzer = StockSentimentAnalyzer(
        st.session_state.stock_extractor,
        st.session_state.llm_client
    )
if 'hot_posts' not in st.session_state:
    st.session_state.hot_posts = []
if 'selected_posts' not in st.session_state:
    st.session_state.selected_posts = set()
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}


# ==================== 分析函数 ====================
def _analyze_selected_posts():
    """分析选中的帖子"""
    selected_tids = list(st.session_state.selected_posts)
    all_posts_content = []

    for tid in selected_tids:
        posts = st.session_state.nga_crawler.get_full_thread(tid, max_pages=2)
        valid = [p for p in posts if p.content and len(p.content) > 15]
        all_posts_content.extend([p.content for p in valid[:15]])

    if not all_posts_content:
        st.warning("选中的帖子内容不足")
        return

    analyzer = st.session_state.stock_sentiment_analyzer
    stock_sentiments = analyzer.analyze(all_posts_content)

    results = st.session_state.llm_client.batch_analyze(all_posts_content[:20])
    report = SentimentAggregator.aggregate(results)

    stock_list = [{"name": s.name, "code": s.code} for s in stock_sentiments[:10]]
    prices = PriceFetcher.get_batch_realtime_with_names(stock_list)

    result_key = f"batch_{','.join(map(str, selected_tids))}"
    st.session_state.analysis_results[result_key] = {
        'report': report,
        'stock_sentiments': stock_sentiments,
        'prices': prices,
        'selected_tids': selected_tids,
    }


def _render_stock_card(stock, price_data):
    """渲染单只股票卡片"""
    if stock.bullish_ratio > 0.6:
        border_color = "#4caf50"
    elif stock.bearish_ratio > 0.6:
        border_color = "#f44336"
    else:
        border_color = "#9e9e9e"

    conf_emoji = "⭐⭐" if stock.total_mentions > 2 else "⭐"

    price_str = ""
    if price_data.get('price'):
        change = price_data.get('change_pct', 0)
        change_emoji = "▲" if change >= 0 else "▼"
        price_str = f'<div style="font-size:0.75rem;">现价: ¥{price_data["price"]} {change_emoji}{change:.1f}%</div>'

    total = stock.bullish_posts + stock.bearish_posts + stock.neutral_posts
    if total > 0:
        bull_pct = int(stock.bullish_ratio * 100)
        bear_pct = int(stock.bearish_ratio * 100)
        neut_pct = 100 - bull_pct - bear_pct
        sentiment_bar = (
            f'<div style="display:flex;height:6px;border-radius:3px;overflow:hidden;margin:5px 0;">'
            f'<div style="flex:{bull_pct};background:#4caf50;"></div>'
            f'<div style="flex:{neut_pct};background:#9e9e9e;"></div>'
            f'<div style="flex:{bear_pct};background:#f44336;"></div></div>'
        )
    else:
        sentiment_bar = ""

    quote = stock.key_quotes[0] if stock.key_quotes else ""
    if quote:
        quote_text = quote[:35] + "..." if len(quote) > 35 else quote
        quote_html = f'<div style="font-size:0.7rem;color:#666;font-style:italic;margin-top:5px;">{quote_text}</div>'
    else:
        quote_html = ""

    # 使用单行 HTML 避免 markdown 解析问题
    card_html = (
        f'<div style="border:2px solid {border_color};border-radius:12px;padding:12px;margin:6px 0;background:#fff;">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="font-weight:bold;">{stock.name}</span>'
        f'<span style="font-size:0.75rem;color:#999;">{stock.code} {conf_emoji}</span></div>'
        f'<div style="font-size:0.8rem;margin-top:4px;color:#555;">'
        f'提及{stock.total_mentions}次 | 看涨{stock.bullish_posts} 看跌{stock.bearish_posts}</div>'
        f'{sentiment_bar}'
        f'{price_str}'
        f'{quote_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


def _render_stock_list_item(stock, price_data):
    """渲染股票列表项（紧凑版）"""
    sentiment_emoji = "🟢" if stock.bullish_ratio > 0.6 else "🔴" if stock.bearish_ratio > 0.6 else "⚪"
    price_info = f"¥{price_data['price']}" if price_data.get('price') else "--"
    st.caption(f"{sentiment_emoji} {stock.name}({stock.code}) - 提及{stock.total_mentions}次 - {price_info}")


def _render_analysis_results(stock_filter, sort_by):
    """渲染分析结果"""
    latest_key = list(st.session_state.analysis_results.keys())[-1]
    result = st.session_state.analysis_results[latest_key]

    stock_sentiments = result['stock_sentiments']
    prices = result.get('prices', {})
    report = result['report']

    if stock_filter:
        stock_sentiments = [
            s for s in stock_sentiments
            if stock_filter in s.name or stock_filter in s.code
        ]

    if sort_by == "提及次数":
        stock_sentiments.sort(key=lambda x: x.total_mentions, reverse=True)
    elif sort_by == "看涨比例":
        stock_sentiments.sort(key=lambda x: x.bullish_ratio, reverse=True)
    elif sort_by == "看跌比例":
        stock_sentiments.sort(key=lambda x: x.bearish_ratio, reverse=True)
    elif sort_by == "情感得分":
        stock_sentiments.sort(key=lambda x: x.avg_sentiment_score, reverse=True)

    emoji, label, desc = SignalInterpreter.emotion_label(report.get('emotion_index', 50))
    st.markdown(f"**{desc}**")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("📈 看涨", f"{report.get('bullish_ratio', 0)*100:.0f}%")
    with c2:
        st.metric("➡️ 中性", f"{report.get('neutral_ratio', 0)*100:.0f}%")
    with c3:
        st.metric("📉 看跌", f"{report.get('bearish_ratio', 0)*100:.0f}%")

    st.markdown("**🔥 股票推荐**")
    cols = st.columns(3)
    for i, stock in enumerate(stock_sentiments[:9]):
        with cols[i % 3]:
            _render_stock_card(stock, prices.get(stock.code, {}))

    if len(stock_sentiments) > 9:
        with st.expander(f"查看其余 {len(stock_sentiments)-9} 只股票"):
            for stock in stock_sentiments[9:]:
                _render_stock_list_item(stock, prices.get(stock.code, {}))


# ==================== 顶部标题 ====================
st.title("📈 NGA 大时代情绪监控 v3")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("🔥 情绪指数", "--", "--")
with col2:
    st.metric("📊 监控帖子", f"{len(st.session_state.hot_posts)}", "")
with col3:
    st.metric("🎯 已分析帖数", f"{len(st.session_state.analysis_results)}", "")
with col4:
    st.metric("⏰ 更新时间", datetime.now().strftime("%H:%M"), "")

st.divider()

# ==================== 两栏布局 ====================
left_col, right_col = st.columns([1, 2])

# --- 左栏：帖子列表 + 抓取按钮 ---
with left_col:
    st.subheader("📰 热门帖子")

    if st.button("📡 抓取大时代热门", use_container_width=True):
        with st.spinner("正在抓取热门帖子..."):
            posts = st.session_state.board_crawler.get_hot_posts(fid='706', pages=3)
            st.session_state.hot_posts = posts
            st.session_state.selected_posts = set()
            st.success(f"抓取到 {len(posts)} 个帖子！")

    if not st.session_state.hot_posts:
        st.info("点击上方按钮抓取热门帖子")
    else:
        selected_count = len(st.session_state.selected_posts)
        if selected_count > 0:
            if st.button(f"🎯 分析选中的 {selected_count} 个帖子", use_container_width=True, type="primary"):
                with st.spinner(f"正在分析 {selected_count} 个帖子..."):
                    _analyze_selected_posts()

        st.divider()

        for i, post in enumerate(st.session_state.hot_posts[:20]):
            age_h = (datetime.now().timestamp() - post.lastpost.timestamp()) / 3600
            col_cb, col_info = st.columns([0.1, 0.9])

            with col_cb:
                is_selected = st.checkbox(
                    "",
                    value=post.tid in st.session_state.selected_posts,
                    key=f"cb_{post.tid}",
                    label_visibility="collapsed"
                )
                if is_selected:
                    st.session_state.selected_posts.add(post.tid)
                else:
                    st.session_state.selected_posts.discard(post.tid)

            with col_info:
                st.markdown(f"""
                <div class="hot-post">
                    <div style="font-size:0.85rem; font-weight:500;">{post.subject[:25]}{'...' if len(post.subject) > 25 else ''}</div>
                    <div style="font-size:0.7rem; color:#999;">
                        #{post.tid} | 回复:{post.replies} | {age_h:.0f}h前
                    </div>
                </div>
                """, unsafe_allow_html=True)

# --- 右栏：分析结果 ---
with right_col:
    st.subheader("🎯 分析结果")

    filter_col, sort_col = st.columns(2)
    with filter_col:
        stock_filter = st.text_input("🔍 过滤股票", "", placeholder="输入名称或代码")
    with sort_col:
        sort_by = st.selectbox(
            "📊 排序方式",
            ["提及次数", "看涨比例", "看跌比例", "情感得分"],
            index=0
        )

    if not st.session_state.analysis_results:
        st.info("👈 在左侧选择帖子并点击「分析选中的帖子」")
    else:
        _render_analysis_results(stock_filter, sort_by)


# ==================== 底部 ====================
st.divider()
st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border-radius: 15px; padding: 20px; text-align: center;">
    <h3>⚠️ 风险提示</h3>
    <p>本工具基于 NGA 散户情绪分析，仅供学习研究，不构成任何投资建议！</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
**📖 如何使用本工具：**
1. 点击左侧「📡 抓取大时代热门」获取最新热门帖子
2. 勾选感兴趣的帖子（可多选）
3. 点击「分析选中的帖子」进行批量分析
4. 在右侧查看股票卡片、情绪分布和实时价格
5. 结合自己判断做出投资决策
""")

st.divider()
st.caption(f"NGAQuant v3.0 | 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
