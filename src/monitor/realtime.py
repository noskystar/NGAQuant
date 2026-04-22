"""
NGA实时监控模块
定时轮询帖子，情绪变化时自动推送通知
"""
import time
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Callable, Dict
import threading
from dataclasses import dataclass, asdict

from src.crawler.nga_client import NGACrawler, NGAPost
from src.analyzer.sentiment import LLMClient, SentimentAggregator, SentimentResult
from src.analyzer.stock_extractor import analyze_stock_mentions
from src.notifier.feishu import FeishuNotifier
from src.database.db import db
from src.config import config

@dataclass
class MonitorState:
    """监控状态"""
    tid: str
    last_check_time: datetime
    last_emotion_index: float
    last_post_count: int
    check_count: int = 0

class ThreadMonitor:
    """单个帖子监控器"""
    
    def __init__(
        self,
        tid: str,
        interval: int = 300,
        emotion_threshold: float = 0.15,
        notifier: Optional[FeishuNotifier] = None,
        on_change: Optional[Callable] = None
    ):
        self.tid = tid
        self.interval = interval
        self.emotion_threshold = emotion_threshold
        self.notifier = notifier
        self.on_change = on_change
        
        # 状态
        self.state = MonitorState(
            tid=tid,
            last_check_time=datetime.now(),
            last_emotion_index=50.0,
            last_post_count=0,
            check_count=0
        )
        
        # 组件
        self.crawler = NGACrawler()
        self.llm_client = LLMClient(api_key=config.minimax.api_key)
        
        # 运行状态
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self):
        """启动监控"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        
        print(f"✅ 开始监控帖子 {self.tid}，检查间隔 {self.interval}秒")
    
    def stop(self):
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print(f"🛑 已停止监控帖子 {self.tid}")
    
    def _monitor_loop(self):
        """监控循环"""
        # 首次执行立即检查
        self._check_once()
        
        while self._running:
            time.sleep(self.interval)
            if self._running:
                self._check_once()
    
    def _check_once(self):
        """执行一次检查"""
        try:
            print(f"\n🔍 [{datetime.now().strftime('%H:%M:%S')}] 检查帖子 {self.tid}...")
            
            # 1. 爬取帖子
            posts = self.crawler.get_full_thread(self.tid, max_pages=3)
            
            if not posts:
                print(f"⚠️ 未能获取帖子 {self.tid} 内容")
                return
            
            current_count = len(posts)
            new_posts = current_count - self.state.last_post_count
            
            print(f"   帖子总数: {current_count} (新增 {new_posts} 条)")
            
            # 2. 提取股票
            stocks = analyze_stock_mentions([p.content for p in posts])
            
            # 3. 情感分析（只分析新内容）
            if new_posts > 0:
                recent_posts = posts[-min(new_posts, 20):]  # 最新的20条
                contents = [p.content for p in recent_posts if len(p.content) > 20]
                
                if contents:
                    sentiment_results = self.llm_client.batch_analyze(contents)
                    report = SentimentAggregator.aggregate(sentiment_results)
                    
                    current_emotion = report.get('emotion_index', 50.0)
                    
                    # 4. 检测情绪变化
                    emotion_change = abs(current_emotion - self.state.last_emotion_index)
                    emotion_change_pct = emotion_change / 100.0
                    
                    print(f"   当前情绪指数: {current_emotion:.1f}")
                    print(f"   情绪变化: {emotion_change:.1f} ({emotion_change_pct*100:.1f}%)")
                    
                    # 情绪变化超过阈值，发送通知
                    if emotion_change_pct >= self.emotion_threshold:
                        self._send_notification(report, stocks, emotion_change)
                    
                    # 更新状态
                    self.state.last_emotion_index = current_emotion
                    self.state.check_count += 1
            
            self.state.last_post_count = current_count
            self.state.last_check_time = datetime.now()
            
        except Exception as e:
            print(f"❌ 检查失败: {e}")
    
    def _send_notification(self, report: dict, stocks: list, emotion_change: float):
        """发送通知"""
        emotion_idx = report.get('emotion_index', 50.0)
        market_emotion = report.get('market_emotion', '中性')
        
        # 构建通知内容
        title = f"📈 NGAQuant 情绪告警 - 帖子 {self.tid}"
        
        direction = "📈 看涨" if emotion_idx > self.state.last_emotion_index else "📉 看跌"
        
        content = f"""## 🚨 情绪变化告警

**帖子**: {self.tid}
**检测时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### 📊 情绪变化
- 变化幅度: **{emotion_change:.1f}点** {direction}
- 当前情绪: **{emotion_idx:.1f}/100** ({market_emotion})
- 上一情绪: **{self.state.last_emotion_index:.1f}/100**

### 🔥 热门股票
"""
        
        # 添加股票信息
        for stock in stocks[:5]:
            content += f"- {stock.name} ({stock.code}): {stock.mention_count}次提及\n"
        
        # 投资建议
        content += f"\n### 💡 建议\n"
        if emotion_idx > 70:
            content += "⚠️ 市场情绪过热，建议谨慎操作\n"
        elif emotion_idx < 30:
            content += "✅ 市场情绪低迷，可能是布局机会\n"
        else:
            content += "➡️ 市场情绪中性，建议观望\n"
        
        # 发送通知
        if self.notifier:
            self.notifier.send_markdown(title, content)
            print(f"   ✅ 已发送飞书通知")
        else:
            print(f"   📧 通知内容:\n{content}")
        
        # 回调
        if self.on_change:
            self.on_change(report, stocks, emotion_change)


class MultiThreadMonitor:
    """多帖子监控管理器"""
    
    def __init__(self, max_threads: int = 10):
        self.max_threads = max_threads
        self.monitors: Dict[str, ThreadMonitor] = {}
        self._lock = threading.Lock()
    
    def add_thread(self, tid: str, interval: Optional[int] = None) -> bool:
        """添加监控帖子"""
        with self._lock:
            if tid in self.monitors:
                print(f"⚠️ 帖子 {tid} 已在监控列表中")
                return False
            
            if len(self.monitors) >= self.max_threads:
                print(f"❌ 已达到最大监控数量 ({self.max_threads})")
                return False
            
            # 创建通知器
            notifier = None
            if config.feishu.webhook_url:
                notifier = FeishuNotifier(config.feishu.webhook_url)
            
            # 创建监控器
            interval = interval or config.monitor.default_interval
            threshold = config.monitor.emotion_change_threshold
            
            monitor = ThreadMonitor(
                tid=tid,
                interval=interval,
                emotion_threshold=threshold,
                notifier=notifier
            )
            
            self.monitors[tid] = monitor
            monitor.start()
            return True
    
    def remove_thread(self, tid: str) -> bool:
        """移除监控帖子"""
        with self._lock:
            if tid not in self.monitors:
                return False
            
            self.monitors[tid].stop()
            del self.monitors[tid]
            return True
    
    def list_monitors(self) -> List[Dict]:
        """列出所有监控"""
        with self._lock:
            return [
                {
                    'tid': tid,
                    'state': asdict(monitor.state)
                }
                for tid, monitor in self.monitors.items()
            ]
    
    def stop_all(self):
        """停止所有监控"""
        with self._lock:
            for monitor in self.monitors.values():
                monitor.stop()
            self.monitors.clear()


# 全局监控管理器实例
monitor_manager = MultiThreadMonitor()


def start_monitor(tid: str, interval: int = 300) -> bool:
    """便捷函数：启动单个帖子监控"""
    return monitor_manager.add_thread(tid, interval)


def stop_monitor(tid: str) -> bool:
    """便捷函数：停止单个帖子监控"""
    return monitor_manager.remove_thread(tid)


def stop_all_monitors():
    """便捷函数：停止所有监控"""
    monitor_manager.stop_all()


# 测试
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python realtime.py <tid> [interval_seconds]")
        print("示例: python realtime.py 12345678 300")
        sys.exit(1)
    
    tid = sys.argv[1]
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    
    print(f"🚀 启动实时监控: 帖子 {tid}, 间隔 {interval}秒")
    print("按 Ctrl+C 停止监控\n")
    
    # 验证配置
    errors = config.validate()
    if errors:
        print("❌ 配置错误:")
        for error in errors:
            print(f"   - {error}")
        sys.exit(1)
    
    # 启动监控
    monitor = ThreadMonitor(tid=tid, interval=interval)
    monitor.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 正在停止监控...")
        monitor.stop()
        print("👋 已退出")
