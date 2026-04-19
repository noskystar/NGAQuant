"""
NGAQuant Web Dashboard
NGA大时代股票情绪分析器 - Streamlit Web 界面
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import sys
import os
from datetime import datetime
from typing import List, Dict, Optional
import json

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.nga_client import NGACrawler, NGAPost
from src.analyzer.sentiment import LLMClient, SentimentAggregator, SentimentType
from src.analyzer.stock_extractor import extract_stocks, analyze_stock_mentions, Stock
from src.config import ConfigManager

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="NGAQuant - NGA大时代情绪分析",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义样式 ====================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .emotion-gauge {
        text-align: center;
        font-size: 3rem;
        font-weight: bold;
    }
    .bullish { color: #ff4b4b; }
    .bearish { color: #00b4d8; }
    .neutral { color: #808080; }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
    }
    .stock-tag {
        background-color: #e8f4f8;
        border-radius: 5px;
        padding: 0.3rem 0.6rem;
        margin: 0.2rem;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)


# ==================== 初始化状态 ====================
def init_session_state():
    """初始化会话状态"""
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = None
    if 'posts' not in st.session_state:
        st.session_state.posts = []
    if 'current_tid' not in st.session_state:
        st.session_state.current_tid = None
    if 'config' not in st.session_state:
        st.session_state.config = None
    if 'llm_client' not in st.session_state:
        st.session_state.llm_client = None


def get_llm_client(api_key: str) -> LLMClient:
    """获取或创建 Kimi 客户端"""
    if not api_key:
        return None
    return LLMClient(api_key=api_key)


def parse_posts_for_analysis(posts: List[NGAPost]) -> List[str]:
    """将帖子解析为分析文本列表"""
    texts = []
    for post in posts:
        if post.content and len(post.content) > 10:
            texts.append(post.content)
    return texts


# ==================== 侧边栏配置 ====================
def render_sidebar():
    """渲染侧边栏配置"""
    with st.sidebar:
        st.title("⚙️ 配置")
        
        # API Key 配置
        st.subheader("🔑 MiniMax API Key")
        api_key = st.text_input(
            "输入 API Key",
            type="password",
            help="从 https://api.minimaxi.com/ 获取",
            placeholder="sk-..."
        )
        
        if api_key:
            st.session_state.llm_client = get_llm_client(api_key)
            st.success("✅ API Key 已配置")
        else:
            st.warning("⚠️ 请输入 MiniMax API Key 才能进行情感分析")
        
        # 加载配置
        try:
            config = ConfigManager()
            errors = config.validate()
            if errors:
                for err in errors:
                    st.error(err)
            st.session_state.config = config
        except Exception as e:
            st.error(f"配置加载失败: {e}")
        
        st.divider()
        
        # NGA Cookie 配置
        st.subheader("🌐 NGA Cookie (可选)")
        nga_cookie = st.text_input(
            "NGA Cookie",
            type="password",
            help="访问需要登录的帖子时需要",
            placeholder="ngaPassportU=..."
        )
        
        st.divider()
        
        # 分析参数
        st.subheader("📊 分析参数")
        max_pages = st.slider("最大页数", 1, 20, 5)
        max_hours = st.select_slider(
            "时间范围",
            options=[0, 24, 48, 72, 168],
            value=72,
            format_func=lambda x: "全部" if x == 0 else f"近 {x} 小时"
        )
        min_confidence = st.slider("最低置信度", 0.0, 1.0, 0.6)
        
        return {
            'api_key': api_key,
            'nga_cookie': nga_cookie,
            'max_pages': max_pages,
            'max_hours': max_hours,
            'min_confidence': min_confidence
        }


# ==================== 情绪仪表盘 ====================
def render_emotion_gauge(emotion_index: float):
    """渲染情绪仪表盘"""
    # 将 0-100 的情绪指数转换为颜色
    if emotion_index >= 70:
        color = "#ff4b4b"  # 贪婪 - 红色
        label = "贪婪 😱"
    elif emotion_index <= 30:
        color = "#00b4d8"  # 恐惧 - 蓝色
        label = "恐惧 😨"
    else:
        color = "#808080"  # 中性 - 灰色
        label = "中性 😐"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=emotion_index,
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': 'white',
            'borderwidth': 2,
            'bordercolor': 'gray',
            'steps': [
                {'range': [0, 30], 'color': '#00b4d8'},
                {'range': [30, 70], 'color': '#808080'},
                {'range': [70, 100], 'color': '#ff4b4b'},
            ],
        },
        number={'font': {'size': 48}},
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"<p style='text-align:center; color:{color}; font-size:1.5rem; font-weight:bold;'>{label}</p>", unsafe_allow_html=True)


def render_sentiment_pie(dist: Dict):
    """渲染情感分布饼图"""
    labels = ['强烈看涨', '轻度看涨', '中性', '轻度看跌', '强烈看跌']
    values = [
        dist.get('strong_bullish', 0),
        dist.get('slightly_bullish', 0),
        dist.get('neutral', 0),
        dist.get('slightly_bearish', 0),
        dist.get('strong_bearish', 0)
    ]
    colors = ['#ff4b4b', '#ff9999', '#808080', '#99ccff', '#00b4d8']
    
    fig = px.pie(
        values=values,
        names=labels,
        title='情感分布',
        color=labels,
        color_discrete_map={
            '强烈看涨': '#ff4b4b',
            '轻度看涨': '#ff9999',
            '中性': '#808080',
            '轻度看跌': '#99ccff',
            '强烈看跌': '#00b4d8'
        }
    )
    fig.update_layout(
        height=300,
        showlegend=True,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)


def render_stock_chart(top_stocks: List[tuple]):
    """渲染热门股票柱状图"""
    if not top_stocks:
        st.info("暂无股票数据")
        return
    
    df = pd.DataFrame(top_stocks[:10], columns=['股票', '提及次数'])
    
    fig = px.bar(
        df,
        x='股票',
        y='提及次数',
        title='热门股票提及次数',
        color='提及次数',
        color_continuous_scale='Blues'
    )
    fig.update_layout(
        height=300,
        showlegend=False,
        xaxis_title="",
        yaxis_title="提及次数",
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)



def render_stock_radar(results: Dict, top_stocks: List[tuple]):
    """渲染股票推荐雷达图"""
    if not top_stocks:
        return
    
    # 取前5只股票，每只计算"推荐度"
    # 推荐度 = (看涨帖子中提及该股次数 * 1.0 + 中性 * 0.3 - 看跌 * 0.5) / 总帖子数
    # 这里简化为：提及次数 * 情绪指数/100
    bullish = results.get('bullish_ratio', 0)
    emotion = results.get('emotion_index', 50) / 100
    
    names = [s[0] for s in top_stocks[:6]]
    mentions = [s[1] for s in top_stocks[:6]]
    
    # 推荐度得分（0-100）
    scores = [int(m * emotion * 10) for m in mentions]
    # 最低10分
    scores = [max(s, 10) for s in scores]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores + [scores[0]],
        theta=names + [names[0]],
        fill='toself',
        fillcolor='rgba(31, 119, 180, 0.3)',
        line=dict(color='#1f77b4'),
        marker=dict(size=6),
        name='推荐度'
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        height=300,
        title="股票推荐度雷达图",
        showlegend=False,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)


def render_sentiment_bubble(results: Dict, posts: List):
    """渲染情感气泡图（按楼层分布）"""
    # 使用 session state 中的原始分析结果
    analysis = st.session_state.get('analysis_results', {})
    
    bubble_data = []
    for i, r in enumerate(analysis.get('post_results', [])):
        sentiment = r.get('sentiment', 'neutral')
        confidence = r.get('confidence', 0.5)
        floor = r.get('floor', i * 10)
        
        if sentiment == '看涨' or sentiment == '轻度看涨':
            val, color = 1, '#ff4b4b'
        elif sentiment == '看跌' or sentiment == '轻度看跌':
            val, color = -1, '#00b4d8'
        else:
            val, color = 0, '#808080'
        
        bubble_data.append({
            'floor': floor,
            'value': val,
            'confidence': confidence,
            'color': color,
            'sentiment': sentiment
        })
    
    if not bubble_data:
        return
    
    df = pd.DataFrame(bubble_data)
    
    fig = go.Figure()
    colors_map = {'看涨': '#ff4b4b', '轻度看涨': '#ff9999', '中性': '#808080', '轻度看跌': '#99ccff', '看跌': '#00b4d8'}
    
    for sent, grp in df.groupby('sentiment'):
        fig.add_trace(go.Scatter(
            x=grp['floor'],
            y=grp['value'],
            mode='markers',
            marker=dict(size=grp['confidence'] * 30 + 5, color=colors_map.get(sent, '#808080')),
            name=sent,
            text=[f"#{f} {s}" for f, s in zip(grp['floor'], grp['sentiment'])],
            hovertemplate="#%{text}<br>情绪: %{marker.color}<extra></extra>"
        ))
    
    fig.update_layout(
        height=250,
        xaxis_title="楼层",
        yaxis_title="情绪（红=看涨 蓝=看跌）",
        yaxis=dict(range=[-1.5, 1.5], tickvals=[-1, 0, 1], ticktext=['看跌', '中性', '看涨']),
        margin=dict(l=20, r=20, t=30, b=40),
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)


def render_stock_cards(top_stocks: List[tuple], results: Dict):
    """渲染股票推荐卡片"""
    if not top_stocks:
        return
    
    bullish = results.get('bullish_ratio', 0)
    emotion = results.get('emotion_index', 50)
    
    for name, count in top_stocks[:8]:
        # 计算推荐度得分
        score = int(count * emotion / 10)
        score = max(10, min(100, score))
        
        if score >= 70:
            tag, tag_color = "🔥 强烈推荐", "#ff4b4b"
        elif score >= 50:
            tag, tag_color = "✅ 谨慎关注", "#ffaa00"
        else:
            tag, tag_color = "👀 观察", "#808080"
        
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{name}**")
            with col2:
                st.markdown(f'<span style="color:{tag_color};font-weight:bold">{tag}</span>', unsafe_allow_html=True)
            with col3:
                st.markdown(f"提及 **{count}** 次")
            st.markdown("---")




# ==================== 分析主界面 ====================
def render_analysis_section(config: Dict):
    """渲染分析主界面"""
    st.header("🔍 帖子分析")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        tid = st.text_input(
            "📝 输入 NGA 帖子 ID (tid)",
            placeholder="例如: 25914502",
            help="从帖子 URL 中提取，例如 https://bbs.nga.cn/read.php?tid=25914502"
        )
    with col2:
        st.write("")  # 占位
        st.write("")
        analyze_btn = st.button("🚀 开始分析", type="primary", use_container_width=True)
    
    if analyze_btn and tid:
        if not st.session_state.llm_client:
            st.error("请先在侧边栏配置 MiniMax API Key")
            return
        
        with st.spinner("正在爬取帖子..."):
            try:
                crawler = NGACrawler(cookie=config.get('nga_cookie', ''))
                posts = crawler.get_full_thread(
                    tid,
                    max_pages=config.get('max_pages', 5),
                    max_hours=config.get('max_hours', 72)
                )
                
                if not posts:
                    st.error("未爬取到帖子，请检查 TID 是否正确，或尝试配置 Cookie")
                    return
                
                st.session_state.posts = posts
                st.session_state.current_tid = tid
                st.success(f"✅ 成功爬取 {len(posts)} 条帖子")
                
            except Exception as e:
                st.error(f"爬取失败: {e}")
                return
        
        # 情感分析
        with st.spinner("正在进行情感分析（这可能需要几分钟）..."):
            try:
                texts = parse_posts_for_analysis(posts)
                
                # 批量分析
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, text in enumerate(texts):
                    result = st.session_state.llm_client.analyze_sentiment(text)
                    results.append(result)
                    progress_bar.progress((i + 1) / len(texts))
                    status_text.text(f"分析第 {i+1}/{len(texts)} 条帖子...")
                
                # 聚合结果
                aggregated = SentimentAggregator.aggregate(results)
                st.session_state.analysis_results = aggregated
                
                # 保存每条帖子的情感结果（用于气泡图）
                aggregated['post_results'] = [
                    {'floor': posts[i].floor, 'sentiment': r.sentiment.value, 'confidence': r.confidence}
                    for i, r in enumerate(results) if i < len(posts)
                ]
                
                # 提取股票
                all_text = "\n".join(texts)
                stocks = analyze_stock_mentions(texts)
                aggregated['top_stocks'] = [(s.name, s.mention_count) for s in stocks[:10]]
                
                st.success("✅ 分析完成！")
                st.rerun()
                
            except Exception as e:
                st.error(f"分析失败: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    elif analyze_btn and not tid:
        st.warning("请输入帖子 ID")


# ==================== 结果展示 ====================
def render_results():
    """渲染分析结果"""
    if not st.session_state.analysis_results:
        st.info("👈 输入帖子 ID 开始分析")
        return
    
    results = st.session_state.analysis_results
    posts = st.session_state.posts
    
    st.divider()
    st.header("📊 分析结果")
    
    # 概览指标
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("情绪指数", f"{results['emotion_index']:.1f}", 
                  delta="贪婪" if results['emotion_index'] > 70 else "恐惧" if results['emotion_index'] < 30 else "中性")
    with col2:
        st.metric("分析帖子数", results['total_posts'])
    with col3:
        st.metric("看涨比例", f"{results['bullish_ratio']*100:.1f}%", 
                  delta="↑" if results['bullish_ratio'] > 0.5 else "↓")
    with col4:
        st.metric("看跌比例", f"{results['bearish_ratio']*100:.1f}%",
                  delta="↓" if results['bearish_ratio'] > 0.3 else "")
    with col5:
        st.metric("平均置信度", f"{results['avg_confidence']:.2f}")
    
    st.divider()
    
    # 详细图表
    col_left, col_right = st.columns(2)
    
    with col_left:
        render_emotion_gauge(results['emotion_index'])
    with col_right:
        render_sentiment_pie(results['sentiment_distribution'])
    
    st.divider()
    
    # 股票分析
    st.subheader("📈 热门股票")
    
    if results.get('top_stocks'):
        # 股票推荐卡片（横向排列）
        render_stock_cards(results['top_stocks'], results)
        
        # 两列：柱状图 + 雷达图
        col_bar, col_radar = st.columns(2)
        with col_bar:
            render_stock_chart(results['top_stocks'])
        with col_radar:
            render_stock_radar(results, results['top_stocks'])
        
        # 股票标签展示
        st.markdown("**股票标签：**")
        stock_tags = ""
        for name, count in results['top_stocks'][:15]:
            stock_tags += f'<span class="stock-tag">{name} ({count})</span>'
        st.markdown(stock_tags, unsafe_allow_html=True)
    else:
        st.info("未提取到股票信息，请尝试在帖子内容中包含股票代码或名称")
    
    # 情感气泡图
    st.subheader("📊 情感分布（按楼层）")
    render_sentiment_bubble(results, posts)
    
    st.divider()
    
    # 投资建议
    st.subheader("💡 投资建议")
    
    emotion = results.get('market_emotion', '中性')
    bullish_ratio = results.get('bullish_ratio', 0)
    bearish_ratio = results.get('bearish_ratio', 0)
    
    if emotion == "贪婪":
        recommendation = """
        🚨 **当前市场情绪处于贪婪状态**
        
        历史经验表明，当散户普遍贪婪时，往往是反向指标。建议：
        - ⚠️ 谨慎追高，避免盲目入场
        - 📝 考虑分批减仓，锁定利润
        - 🛡️ 做好止损准备，控制仓位
        """
    elif emotion == "恐惧":
        recommendation = """
        🎯 **当前市场情绪处于恐惧状态**
        
        当散户普遍恐惧时，可能存在布局机会。建议：
        - ✅ 可以关注优质资产的逢低买入机会
        - 📝 控制仓位，分批建仓
        - 🔍 深入研究基本面，避免踩雷
        """
    else:
        recommendation = f"""
        ⚖️ **当前市场情绪中性**
        
        看涨 {bullish_ratio*100:.1f}% | 看跌 {bearish_ratio*100:.1f}%
        
        市场情绪较为平衡，建议：
        - 📊 保持现有仓位
        - 🔍 等待明确信号
        - 📝 持续关注情绪变化
        """
    
    st.markdown(recommendation)
    
    st.divider()
    
    # 帖子详情
    with st.expander("📋 查看原始帖子内容"):
        for i, post in enumerate(posts[:20]):  # 只显示前20条
            st.markdown(f"**#{post.floor} | {post.author} | {post.timestamp.strftime('%Y-%m-%d %H:%M') if hasattr(post.timestamp, 'strftime') else post.timestamp}**")
            st.text(post.content[:500] + "..." if len(post.content) > 500 else post.content)
            st.divider()


# ==================== 使用说明 ====================
def render_help():
    """渲染帮助说明"""
    with st.expander("❓ 如何使用"):
        st.markdown("""
        ## NGAQuant 使用指南
        
        ### 第一步：获取 API Key
        1. 访问 [MiniMax 控制台](https://api.minimaxi.com/)
        2. 注册/登录账号
        3. 在「API Keys」中创建一个新的 API Key
        4. 复制并粘贴到左侧配置栏
        
        ### 第二步：输入帖子 ID
        1. 打开 NGA 论坛的大时代板块
        2. 找到你想分析的帖子
        3. 从 URL 中提取 tid，例如：`https://bbs.nga.cn/read.php?tid=25914502`
        4. tid 就是 `25914502`
        
        ### 第三步：开始分析
        1. 点击「开始分析」按钮
        2. 等待爬虫和 AI 分析完成
        3. 查看情绪指数和投资建议
        
        ### 注意事项
        - 首次分析可能需要几分钟时间
        - 如果帖子需要登录才能访问，需要在配置中填入 Cookie
        - 情绪分析仅供参考，不构成投资建议
        """)
    
    with st.expander("⚠️ 免责声明"):
        st.markdown("""
        **本工具仅供学习研究，不构成投资建议。**
        
        股市有风险，投资需谨慎。
        
        情绪分析结果可能受到以下因素影响：
        - 帖子内容的质量和真实性
        - AI 模型的情感分析能力
        - 市场环境的复杂性
        
        请根据自身判断做出投资决策。
        """)


# ==================== 主函数 ====================
def main():
    init_session_state()
    
    # 标题
    st.markdown('<p class="main-header">📊 NGAQuant - NGA大时代股票情绪分析器</p>', unsafe_allow_html=True)
    st.caption("通过分析 NGA 论坛散户情绪，辅助投资决策 | ⚠️ 仅供参考，不构成投资建议")
    
    # 渲染侧边栏
    config = render_sidebar()
    
    st.divider()
    
    # 渲染分析区
    render_analysis_section(config)
    
    # 渲染结果
    render_results()
    
    # 渲染帮助
    render_help()


if __name__ == "__main__":
    main()
