# 回测系统
"""
策略回测 - 验证情绪指标的有效性
"""
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class TradeSignal:
    """交易信号"""
    timestamp: datetime
    stock_code: str
    action: str  # BUY / SELL / HOLD
    emotion_index: float
    confidence: float
    reason: str

@dataclass
class BacktestResult:
    """回测结果"""
    total_signals: int
    win_count: int
    loss_count: int
    win_rate: float
    avg_return: float
    max_drawdown: float
    sharpe_ratio: float
    signals: List[TradeSignal]

class Backtester:
    """回测引擎"""
    
    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.signals: List[TradeSignal] = []
    
    def add_signal(self, signal: TradeSignal):
        """添加交易信号"""
        self.signals.append(signal)
    
    def run_backtest(self, price_data: Dict[str, List[float]]) -> BacktestResult:
        """
        运行回测
        
        Args:
            price_data: 股票价格数据 {stock_code: [prices]}
            
        Returns:
            回测结果
        """
        if not self.signals:
            return BacktestResult(
                total_signals=0,
                win_count=0,
                loss_count=0,
                win_rate=0.0,
                avg_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                signals=[]
            )
        
        # 简化回测逻辑
        wins = 0
        losses = 0
        returns = []
        
        for i, signal in enumerate(self.signals[:-1]):
            if signal.action == "BUY":
                # 模拟买入，看后续收益
                # 实际应该根据真实价格数据计算
                pass
        
        total = len(self.signals)
        win_rate = wins / total if total > 0 else 0.0
        
        return BacktestResult(
            total_signals=total,
            win_count=wins,
            loss_count=losses,
            win_rate=win_rate,
            avg_return=sum(returns) / len(returns) if returns else 0.0,
            max_drawdown=0.0,  # 简化
            sharpe_ratio=0.0,  # 简化
            signals=self.signals
        )
    
    def generate_report(self, result: BacktestResult) -> str:
        """生成回测报告"""
        report = f"""
========================================
NGAQuant 策略回测报告
========================================

回测时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
初始资金: {self.initial_capital:,.2f} 元

【交易统计】
总信号数: {result.total_signals}
盈利次数: {result.win_count}
亏损次数: {result.loss_count}
胜率: {result.win_rate * 100:.2f}%
平均收益: {result.avg_return * 100:.2f}%
最大回撤: {result.max_drawdown * 100:.2f}%
夏普比率: {result.sharpe_ratio:.2f}

【策略评价】
"""
        
        if result.win_rate > 0.6:
            report += "✅ 策略表现优秀，胜率超过60%\n"
        elif result.win_rate > 0.5:
            report += "➡️ 策略表现一般，略优于随机\n"
        else:
            report += "⚠️ 策略表现较差，需要优化\n"
        
        return report

# 验证情绪指标有效性
def validate_sentiment_correlation(
    emotion_history: List[float],
    price_changes: List[float]
) -> float:
    """
    验证情绪指数与价格变化的相关性
    
    Returns:
        相关系数 (-1 到 1)
    """
    import numpy as np
    
    if len(emotion_history) != len(price_changes):
        return 0.0
    
    # 计算皮尔逊相关系数
    correlation = np.corrcoef(emotion_history, price_changes)[0, 1]
    
    return correlation
