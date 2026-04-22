#!/usr/bin/env python3
"""
NGAQuant CLI - 命令行工具
"""
import argparse
import sys
import os
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from crawler.nga_client import NGACrawler
from analyzer.stock_extractor import extract_stocks, analyze_stock_mentions
from analyzer.sentiment import LLMClient, SentimentAggregator
from config import config
from history.manager import HistoryManager
from history.trend import EmotionTrend
from recommender.engine import RecommenderEngine
from recommender.models import StrategyType, SignalType
from signals.manager import SignalManager
import json
from datetime import datetime

class NGAQuantCLI:
    """NGAQuant 命令行界面"""
    
    def __init__(self):
        self.crawler = None
        self.llm_client = None
    
    def analyze(self, tid: str, max_pages: int = 5):
        """
        分析指定帖子
        
        Args:
            tid: NGA帖子ID
            max_pages: 最大爬取页数
        """
        print(f"🚀 开始分析帖子 {tid}...")
        print("=" * 60)
        
        # 1. 爬取帖子
        print("\n📥 正在爬取帖子内容...")
        self.crawler = NGACrawler(cookie=config.nga.cookie)
        posts = self.crawler.get_full_thread(tid, max_pages=max_pages)
        
        if not posts:
            print("❌ 爬取失败，请检查帖子ID和网络连接")
            return
        
        print(f"✅ 共爬取 {len(posts)} 条回复")
        
        # 2. 提取股票
        print("\n🔍 提取股票提及...")
        all_content = "\n".join([p.content for p in posts])
        stocks = analyze_stock_mentions([p.content for p in posts])
        
        if stocks:
            print(f"📈 发现 {len(stocks)} 只股票:")
            for stock in stocks[:10]:  # 只显示前10
                print(f"   {stock.name} ({stock.code}) - 提及 {stock.mention_count} 次")
        
        # 3. 情感分析
        print("\n🧠 进行情感分析...")
        self.llm_client = LLMClient(api_key=config.minimax.api_key)
        
        # 只分析楼主和重要回复
        main_posts = [p for p in posts if p.is_main_post or len(p.content) > 50]
        if not main_posts:
            main_posts = posts[:10]  # 取前10条
        
        print(f"   分析 {len(main_posts)} 条关键回复...")
        sentiment_results = self.llm_client.batch_analyze([p.content for p in main_posts])
        
        # 4. 聚合结果
        report = SentimentAggregator.aggregate(sentiment_results)
        
        # 5. 输出报告
        self._print_report(report)

        # 6. 保存到历史记录
        self._save_to_history(tid, posts, report, stocks)

        # 7. 保存结果（兼容旧接口）
        self._save_results(tid, report, stocks)
    
    def _print_report(self, report: dict):
        """打印分析报告"""
        print("\n" + "=" * 60)
        print("📊 情感分析报告")
        print("=" * 60)
        
        # 情绪指数
        emotion_idx = report.get("emotion_index", 50)
        bar_width = 40
        filled = int(emotion_idx / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        print(f"\n市场情绪指数: {emotion_idx:.1f}/100")
        print(f"[{bar}]")
        print(f"整体情绪: {report.get('market_emotion', '未知')}")
        
        # 分布
        print(f"\n情感分布:")
        dist = report.get("sentiment_distribution", {})
        total = report.get("total_posts", 1)
        print(f"   看涨: {(dist.get('strong_bullish', 0) + dist.get('slightly_bullish', 0)) / total * 100:.1f}%")
        print(f"   看跌: {(dist.get('strong_bearish', 0) + dist.get('slightly_bearish', 0)) / total * 100:.1f}%")
        print(f"   中性: {dist.get('neutral', 0) / total * 100:.1f}%")
        
        # 热门股票
        print(f"\n🔥 热门股票:")
        for stock, count in report.get("top_stocks", [])[:5]:
            print(f"   {stock}: {count} 次提及")
        
        # 建议
        print(f"\n💡 投资建议:")
        if emotion_idx > 70:
            print("   ⚠️ 市场情绪过热，建议谨慎，考虑减仓")
        elif emotion_idx < 30:
            print("   ✅ 市场情绪低迷，可能是抄底机会，关注优质标的")
        else:
            print("   ➡️ 市场情绪中性，建议观望或精选个股")
        
        print(f"\n分析置信度: {report.get('avg_confidence', 0) * 100:.1f}%")
    
    def _save_to_history(self, tid: str, posts: list, report: dict, stocks: list):
        """保存到历史记录并与上次对比"""
        valid_posts = [p for p in posts if p.content and len(p.content) > 15]
        # 取关键帖子摘要
        key_posts = []
        for p in valid_posts[:5]:
            snippet = p.content[:100].replace('\n', ' ')
            key_posts.append(f"#{p.floor}: {snippet}...")

        history = HistoryManager()
        fp = history.save_analysis(
            tid=tid,
            total_posts=len(posts),
            valid_posts=len(valid_posts),
            pages_parsed=len(posts) // 20 + 1,
            emotion_data=report,
            top_stocks=stocks,
            key_posts=key_posts,
        )

        # 与上次对比
        prev = history.get_previous(tid)
        latest = history.get_latest(tid)
        if prev and latest and latest.analyzed_at != prev.analyzed_at:
            diff = latest.emotion.emotion_index - prev.emotion.emotion_index
            direction = "↑" if diff > 0 else "↓" if diff < 0 else "→"
            print(f"\n📈 情绪变化: {direction} {abs(diff):.1f} (上次: {prev.emotion.emotion_index:.1f} → 本次: {latest.emotion.emotion_index:.1f})")
            prev_stocks = {s.code: s for s in prev.top_stocks}
            curr_stocks = {s.code: s for s in latest.top_stocks}
            new_codes = set(curr_stocks.keys()) - set(prev_stocks.keys())
            gone_codes = set(prev_stocks.keys()) - set(curr_stocks.keys())
            if new_codes:
                print(f"   🆕 新热门: {', '.join(curr_stocks[c].name for c in new_codes)}")
            if gone_codes:
                print(f"   ➖ 退出热门: {', '.join(prev_stocks[c].name for c in gone_codes)}")
        print(f"\n💾 已保存历史记录: {fp.name}")

    def _save_results(self, tid: str, report: dict, stocks: list):
        """保存分析结果"""
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"nga_{tid}_{timestamp}.json"
        
        data = {
            "tid": tid,
            "timestamp": timestamp,
            "sentiment_report": report,
            "stocks": [{"name": s.name, "code": s.code, "mentions": s.mention_count} for s in stocks[:20]],
        }
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 结果已保存: {filename}")

    def recommend(self, tid_list=None, strategy=StrategyType.SHORT, limit=10, save=False):
        """
        基于历史情绪数据生成股票推荐信号

        Args:
            tid_list: 帖子ID列表（从历史记录读取）
            strategy: SHORT 或 MID
            limit: 返回信号数量
            save: 是否保存信号
        """
        print(f"🎯 生成{'短线' if strategy == StrategyType.SHORT else '中线'}推荐信号...")
        print(f"   策略权重: 情绪×{'0.45' if strategy == StrategyType.SHORT else '0.55'} + 价格×{'0.55' if strategy == StrategyType.SHORT else '0.45'}")
        print()

        # 默认帖子列表
        default_tids = ["45974302", "45502551", "44279886"]
        tids = tid_list or default_tids

        # 收集历史数据
        history = HistoryManager()
        posts_data = []
        for tid in tids:
            records = history.list_records(tid=tid.strip(), limit=5)
            if not records:
                print(f"⚠️  帖子 {tid} 无历史记录，跳过")
                continue
            latest = records[0]
            # 情绪趋势（近3次）
            emotion_trend = [r.emotion.emotion_index for r in records[:3]]
            # 热门股票
            top_stocks = [{"name": s.name, "code": s.code, "mention_count": s.mention_count}
                          for s in latest.top_stocks[:20]]
            posts_data.append({
                "tid": tid,
                "emotion_index": latest.emotion.emotion_index,
                "emotion_trend_3d": emotion_trend,
                "top_stocks": top_stocks,
            })
            print(f"  ✅ {tid}: 情绪 {latest.emotion.emotion_index:.1f}，{len(top_stocks)} 只热门股")

        if not posts_data:
            print("❌ 没有可用的历史数据，请先运行 analyze")
            return

        # 生成信号
        engine = RecommenderEngine()
        signals = engine.generate_all_signals(posts_data, strategy=strategy)
        active = [s for s in signals if s.is_active][:limit]

        if not active:
            print("📭 暂无符合条件的推荐信号")
            return

        # 打印信号
        strategy_label = "短线" if strategy == StrategyType.SHORT else "中线"
        print(f"\n{'='*70}")
        print(f"🎯 {strategy_label}推荐信号（生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')}）")
        print(f"{'='*70}")
        print(f"{'排名':<4} {'股票':<10} {'代码':<8} {'信号':<6} {'强度':<8} {'情绪分':<8} {'价格分':<8} {'综合分':<8} {'来源'}")
        print(f"{'-'*70}")

        for i, sig in enumerate(active, 1):
            emoji = sig.emoji
            strength_color = {"STRONG": "🔥", "MODERATE": "📈", "WEAK": "📊"}.get(sig.strength.value, "")
            valid = sig.valid_until.strftime("%m-%d")
            print(f"{i:<4} {emoji}{sig.stock_name:<8} {sig.stock_code:<8} {sig.signal_type.value:<6} "
                  f"{strength_color}{sig.strength.value:<6} "
                  f"{sig.emotion_index:>5.1f}   {sig.price_factor:>5.1f}   "
                  f"{sig.composite_score:>5.1f}   {sig.source_tid}")

        print(f"\n💡 信号说明:")
        for sig in active[:5]:
            reason_summary = sig.reason.get('trigger', '')
            if 'emotion_reason' in sig.reason:
                reason_summary += f" - {sig.reason['emotion_reason'][:50]}"
            print(f"  {sig.emoji}{sig.stock_name}: {reason_summary}")

        if save:
            mgr = SignalManager()
            paths = mgr.save_batch(active)
            print(f"\n💾 已保存 {len(paths)} 个信号到 data/signals/")

        print(f"\n⚠️  风险提示: 所有信号仅供学习研究，不构成投资建议")


def main():
    parser = argparse.ArgumentParser(
        description="NGAQuant - NGA大时代股票情绪分析器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析指定帖子
  python cli.py analyze --tid 12345678
  
  # 分析前10页
  python cli.py analyze --tid 12345678 --max-pages 10
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # analyze 命令
    analyze_parser = subparsers.add_parser("analyze", help="分析指定帖子")
    analyze_parser.add_argument(
        "--tid", "-t",
        required=True,
        help="NGA帖子ID (tid)"
    )
    analyze_parser.add_argument(
        "--max-pages", "-p",
        type=int,
        default=5,
        help="最大爬取页数 (默认: 5)"
    )
    
    # monitor 命令 (待实现)
    monitor_parser = subparsers.add_parser("monitor", help="监控模式")
    monitor_parser.add_argument("--tid", "-t", required=True, help="帖子ID")
    monitor_parser.add_argument("--interval", "-i", type=int, default=300, help="检查间隔(秒)")

    # history 命令
    history_parser = subparsers.add_parser("history", help="查看历史记录", aliases=[])
    history_sub = history_parser.add_subparsers(dest="history_cmd", help="历史命令")

    # history list
    list_parser = history_sub.add_parser("list", help="列出所有历史记录")
    list_parser.add_argument("--tid", "-t", type=str, default=None, help="筛选指定帖子")
    list_parser.add_argument("--limit", "-l", type=int, default=20, help="显示条数")

    # history show
    show_parser = history_sub.add_parser("show", help="查看某帖子的历史")
    show_parser.add_argument("--tid", "-t", required=True, help="帖子ID")

    # history trend
    trend_parser = history_sub.add_parser("trend", help="查看情绪变化趋势")
    trend_parser.add_argument("--tid", "-t", required=True, help="帖子ID")
    trend_parser.add_argument("--limit", "-l", type=int, default=10, help="显示条数")

    # recommend 命令
    recommend_parser = subparsers.add_parser("recommend", help="生成股票推荐信号")
    recommend_parser.add_argument("--tid", "-t", type=str, default=None, help="基于指定帖子生成（多个逗号分隔）")
    recommend_parser.add_argument("--strategy", "-s", choices=["short", "mid"], default="short", help="策略类型")
    recommend_parser.add_argument("--limit", "-l", type=int, default=10, help="显示条数")
    recommend_parser.add_argument("--save", action="store_true", help="保存信号到历史")

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    if args.command == "history":
        history = HistoryManager()
        if not args.history_cmd:
            history_parser.print_help()
            return

        if args.history_cmd == "list":
            records = history.list_records(tid=args.tid, limit=args.limit)
            if not records:
                print("📭 暂无历史记录")
                return
            print(f"📋 历史记录（共 {len(records)} 条）\n")
            for r in records:
                ts = r.analyzed_at[:16].replace("T", " ")
                idx = r.emotion.emotion_index
                label = r.emotion.emotion_label
                emoji = "🟢" if idx >= 65 else "🔴" if idx <= 35 else "🟡"
                print(f"{emoji} {ts} | tid={r.tid} | 情绪 {idx:.1f}（{label}）| 有效帖子 {r.valid_posts}")
            return

        elif args.history_cmd == "show":
            records = history.list_records(tid=args.tid, limit=20)
            if not records:
                print(f"📭 暂无帖子 {args.tid} 的历史记录")
                return
            for r in records:
                print(f"\n{'='*60}")
                ts = r.analyzed_at[:16].replace("T", " ")
                print(f"🕐 {ts} | 情绪指数: {r.emotion.emotion_index:.1f}（{r.emotion.emotion_label}）")
                print(f"📝 有效帖子: {r.valid_posts}/{r.total_posts} | 爬取页数: {r.pages_parsed}")
                print(f"📊 看涨 {r.emotion.bullish_ratio*100:.0f}% | 中性 {r.emotion.neutral_ratio*100:.0f}% | 看跌 {r.emotion.bearish_ratio*100:.0f}%")
                if r.top_stocks:
                    print(f"🔥 热门股票: {', '.join(f'{s.name}({s.code})' for s in r.top_stocks[:5])}")
                if r.key_posts_summary:
                    print(f"💬 关键帖子:")
                    for post in r.key_posts_summary:
                        print(f"   {post[:80]}")
            return

        elif args.history_cmd == "trend":
            trend_data = history.get_trend(args.tid, limit=args.limit)
            print(EmotionTrend.analyze(trend_data))
            return

    cli = NGAQuantCLI()

    if args.command == "analyze":
        cli.analyze(args.tid, args.max_pages)
    elif args.command == "monitor":
        print("🚧 监控模式开发中...")
    elif args.command == "recommend":
        cli.recommend(
            tid_list=args.tid.split(",") if args.tid else None,
            strategy=StrategyType.MID if args.strategy == "mid" else StrategyType.SHORT,
            limit=args.limit,
            save=args.save,
        )


if __name__ == "__main__":
    main()
