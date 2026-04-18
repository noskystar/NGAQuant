# 持仓管理模块
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
from src.database.db import db, UserPortfolio

@dataclass
class Position:
    """持仓数据"""
    stock_code: str
    stock_name: str
    position: int  # 持仓数量
    avg_cost: float  # 平均成本
    current_price: Optional[float] = None  # 当前价格
    
    @property
    def market_value(self) -> float:
        """市值"""
        if self.current_price:
            return self.position * self.current_price
        return 0.0
    
    @property
    def profit_loss(self) -> float:
        """盈亏"""
        if self.current_price:
            return (self.current_price - self.avg_cost) * self.position
        return 0.0
    
    @property
    def profit_loss_pct(self) -> float:
        """盈亏比例"""
        if self.avg_cost > 0:
            return (self.current_price - self.avg_cost) / self.avg_cost * 100
        return 0.0

class PortfolioManager:
    """持仓管理器"""
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
    
    def add_position(self, stock_code: str, stock_name: str, quantity: int, price: float):
        """添加持仓"""
        session = db.get_session()
        try:
            # 查询现有持仓
            existing = session.query(UserPortfolio).filter_by(
                user_id=self.user_id,
                stock_code=stock_code
            ).first()
            
            if existing:
                # 更新持仓
                total_cost = existing.position * existing.avg_cost + quantity * price
                existing.position += quantity
                existing.avg_cost = total_cost / existing.position
                existing.updated_at = datetime.now()
            else:
                # 新建持仓
                portfolio = UserPortfolio(
                    user_id=self.user_id,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    position=quantity,
                    avg_cost=price
                )
                session.add(portfolio)
            
            session.commit()
            return True
        finally:
            session.close()
    
    def reduce_position(self, stock_code: str, quantity: int):
        """减仓"""
        session = db.get_session()
        try:
            existing = session.query(UserPortfolio).filter_by(
                user_id=self.user_id,
                stock_code=stock_code
            ).first()
            
            if not existing:
                return False
            
            if existing.position <= quantity:
                # 清仓
                session.delete(existing)
            else:
                existing.position -= quantity
                existing.updated_at = datetime.now()
            
            session.commit()
            return True
        finally:
            session.close()
    
    def get_portfolio(self) -> List[Position]:
        """获取全部持仓"""
        session = db.get_session()
        try:
            portfolios = session.query(UserPortfolio).filter_by(
                user_id=self.user_id
            ).all()
            
            positions = []
            for p in portfolios:
                # 获取当前价格（简化，实际需要调用行情API）
                current_price = self._get_current_price(p.stock_code)
                
                positions.append(Position(
                    stock_code=p.stock_code,
                    stock_name=p.stock_name,
                    position=p.position,
                    avg_cost=p.avg_cost,
                    current_price=current_price
                ))
            
            return positions
        finally:
            session.close()
    
    def _get_current_price(self, stock_code: str) -> Optional[float]:
        """获取当前价格（简化实现）"""
        # 实际应该调用 AKShare/Tushare 等行情API
        return None
    
    def get_portfolio_summary(self) -> Dict:
        """获取持仓摘要"""
        positions = self.get_portfolio()
        
        total_cost = sum(p.position * p.avg_cost for p in positions)
        total_value = sum(p.market_value for p in positions)
        total_profit = sum(p.profit_loss for p in positions)
        
        return {
            'total_positions': len(positions),
            'total_cost': total_cost,
            'total_value': total_value,
            'total_profit': total_profit,
            'profit_pct': (total_profit / total_cost * 100) if total_cost > 0 else 0,
            'positions': positions
        }
    
    def analyze_with_sentiment(self, report: dict) -> str:
        """结合情绪分析给出持仓建议"""
        positions = self.get_portfolio()
        emotion_index = report.get('emotion_index', 50)
        
        advice = []
        
        # 整体仓位建议
        if emotion_index > 80:
            advice.append("⚠️ 市场情绪极度贪婪，建议整体减仓至50%以下")
        elif emotion_index < 20:
            advice.append("✅ 市场情绪极度恐慌，建议逐步加仓优质标的")
        
        # 个股建议
        top_stocks = report.get('top_stocks', [])
        hot_stocks = [s[0] for s in top_stocks[:5]]
        
        for pos in positions:
            if pos.stock_name in hot_stocks:
                idx = hot_stocks.index(pos.stock_name)
                if idx < 3 and pos.profit_loss_pct > 20:
                    advice.append(f"📈 {pos.stock_name} 热门且盈利可观，可考虑分批止盈")
                elif idx < 3 and pos.profit_loss_pct < -10:
                    advice.append(f"⚠️ {pos.stock_name} 热门但亏损，关注是否为错杀机会")
        
        return "\n".join(advice) if advice else "➡️ 持仓与市场情绪匹配度一般，建议继续持有观望"