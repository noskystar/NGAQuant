"""
NGAQuant Web Dashboard v2
散户友好版 - 自动发现热门帖子 + 通俗化信号解读
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
from src.analyzer.sentiment import LLMClient, SentimentAggregator
from src.analyzer.stock_extractor import analyze_stock_mentions
from src.analyzer.interpret import SignalInterpreter
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
.hot-post {background: #fff3cd; border-left: 4px solid #ffc107; padding: 10px; margin: 5px 0; border-radius: 5px;}
.signal-card {background: #e8f5e9; border-radius: 12px; padding: 15px; margin: 8px 0;}
.warning-card {background: #ffebee; border-radius: 12px; padding: 15px; margin: 8px 0;}
</style>
""", unsafe_allow_html=True)

# ==================== 初始化 ====================
if 'board_crawler' not in st.session_state:
    st.session_state.board_crawler = BoardCrawler()
if 'nga_crawler' not in st.session_state:
    st.session_state.nga_crawler = NGACrawler(cookie=config.nga.cookie)
if 'hot_posts' not in st.session_state:
    st.session_state.hot_posts = []
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}

# ==================== 侧边栏 ====================
with st.sidebar:
    st.title("📊 NGAQuant")
    st.markdown("**NGA 大时代情绪选股系统**")
    st.divider()
    
    st.subheader("🔄 刷新热门帖")
    if st.button("📰 抓取大时代热门", use_container_width=True):
        with st.spinner("正在抓取热门帖子..."):
            posts = st.session_state.board_crawler.get_hot_posts(fid='706', pages=3)
            st.session_state.hot_posts = posts
            st.success(f"抓取到 {len(posts)} 个帖子！")
    
    st.divider()
    st.subheader("📋 热门帖子列表")
    for p in st.session_state.hot_posts[:15]:
        age_h = (datetime.now().timestamp() - p.lastpost.timestamp()) / 3600
        st.caption(f"#{p.tid} {p.subject[:20]}... ({p.replies}回复 | {age_h:.0f}h前)")

# ==================== 主区域 ====================
st.title("📈 NGA 大时代情绪监控")

# --- KPI 仪表盘 ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🔥 情绪指数", "--", "--")
with col2:
    st.metric("📊 监控帖子", f"{len(st.session_state.hot_posts)}", "")
with col3:
    st.metric("🎯 活跃信号", "0", "")
with col4:
    st.metric("⏰ 更新时间", datetime.now().strftime("%H:%M"), "")

st.divider()

# --- 热门帖子分析区 ---
st.subheader("📰 热门帖子快速分析")

if not st.session_state.hot_posts:
    st.info("👈 点击左侧「抓取热门帖子」开始分析！")
else:
    # 显示前5个热门帖子作为可点击按钮
    cols = st.columns(5)
    for i, (col, post) in enumerate(zip(cols, st.session_state.hot_posts[:5])):
        with col:
            age_h = (datetime.now().timestamp() - post.lastpost.timestamp()) / 3600
            st.markdown(f"""
            <div style="background:#f8f9fa; border-radius:8px; padding:10px; text-align:center;">
                <div style="font-size:0.75rem; color:#666;">{post.subject[:15]}...</div>
                <div style="font-size:0.65rem; color:#999; margin-top:5px;">
                    回复:{post.replies} | {age_h:.0f}h前
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"分析 #{i+1}", key=f"btn_{post.tid}", use_container_width=True):
                with st.spinner(f"正在分析帖子 {post.tid}..."):
                    posts = st.session_state.nga_crawler.get_full_thread(post.tid, max_pages=3)
                    valid = [p for p in posts if p.content and len(p.content) > 15]
                    
                    if valid:
                        llm = LLMClient(api_key=config.minimax.api_key)
                        results = llm.batch_analyze([p.content for p in valid[:20]])
                        report = SentimentAggregator.aggregate(results)
                        stocks = analyze_stock_mentions([p.content for p in valid])
                        
                        emoji, label, desc = SignalInterpreter.emotion_label(report.get('emotion_index', 50))
                        
                        st.session_state.analysis_results[post.tid] = {
                            'report': report,
                            'stocks': stocks[:10],
                            'posts': valid,
                        }
                        
                        st.success(f"分析完成！情绪: {emoji} {label} ({report.get('emotion_index', 0):.1f})")

# --- 分析结果展示 ---
st.divider()
st.subheader("🎯 个股信号解读")

if st.session_state.analysis_results:
    for tid, result in st.session_state.analysis_results.items():
        report = result['report']
        stocks = result['stocks']
        emoji, label, desc = SignalInterpreter.emotion_label(report.get('emotion_index', 50))
        
        with st.expander(f"📊 {emoji} {label} (指数: {report.get('emotion_index', 0):.1f}) - 点击展开详情", expanded=True):
            # 情绪通俗解读
            st.markdown(f"**{desc}**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                bullish = report.get('bullish_ratio', 0) * 100
                st.metric("📈 看涨比例", f"{bullish:.0f}%")
            with col2:
                neutral = report.get('neutral_ratio', 0) * 100
                st.metric("➡️ 中性比例", f"{neutral:.0f}%")
            with col3:
                bearish = report.get('bearish_ratio', 0) * 100
                st.metric("📉 看跌比例", f"{bearish:.0f}%")
            
            # 情绪条形图
            st.markdown("**情感分布：**")
            df_sentiment = pd.DataFrame({
                '类型': ['看涨', '中性', '看跌'],
                '占比': [bullish, neutral, bearish]
            })
            fig = px.bar(df_sentiment, x='类型', y='占比', color='类型',
                        color_discrete_map={'看涨': '#ff6b6b', '中性': '#888', '看跌': '#4ecdc4'})
            fig.update_layout(showlegend=False, height=200)
            st.plotly_chart(fig, use_container_width=True)
            
            # 热门股票
            if stocks:
                st.markdown("**🔥 热门股票：**")
                cols = st.columns(5)
                for i, (col, s) in enumerate(zip(cols, stocks[:5])):
                    with col:
                        st.markdown(f"""
                        <div style="background:#e3f2fd; border-radius:8px; padding:8px; text-align:center;">
                            <div style="font-weight:bold;">{s.name}</div>
                            <div style="font-size:0.7rem; color:#666;">{s.code}</div>
                            <div style="font-size:0.65rem; color:#1976d2;">提及{s.mention_count}次</div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # 更多股票列表
                for s in stocks[5:10]:
                    st.caption(f"  • {s.name}({s.code}) - {s.mention_count}次提及")
else:
    st.info("还没有分析结果。点击上方「分析」按钮开始分析！")

# --- 投资建议区 ---
st.divider()
st.subheader("💡 投资建议")

st.markdown("""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; border-radius: 15px; padding: 20px; text-align: center;">
    <h3>⚠️ 风险提示</h3>
    <p>本工具基于 NGA 散户情绪分析，仅供学习研究，不构成任何投资建议！</p>
    <p>市场有风险，投资需谨慎。</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
**📖 如何使用本工具：**
1. 点击左侧「📰 抓取热门帖子」获取大时代最新热门
2. 点击帖子下方的「分析」按钮进行深度分析
3. 查看情绪指数和热门股票
4. 结合自己判断做出投资决策
""")

# ==================== 页脚 ====================
st.divider()
st.caption(f"NGAQuant v2.0 | 最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
