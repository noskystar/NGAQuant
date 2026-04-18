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
        self.crawler = NGACrawler()
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
        self.llm_client = LLMClient()
        
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
        
        # 6. 保存结果
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
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = NGAQuantCLI()
    
    if args.command == "analyze":
        cli.analyze(args.tid, args.max_pages)
    elif args.command == "monitor":
        print("🚧 监控模式开发中...")


if __name__ == "__main__":
    main()
