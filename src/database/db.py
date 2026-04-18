# 数据库配置
from sqlalchemy import create_engine, Column, String, Float, DateTime, Integer, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path

Base = declarative_base()

class Post(Base):
    """帖子表"""
    __tablename__ = 'posts'
    
    id = Column(String(50), primary_key=True)
    tid = Column(String(20), nullable=False, index=True)
    author = Column(String(100), nullable=False)
    author_uid = Column(String(20))
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    floor = Column(Integer)
    is_main_post = Column(Boolean, default=False)
    sentiment = Column(String(20))  # bullish/bearish/neutral
    sentiment_confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.now)
    
class AnalysisReport(Base):
    """分析报告表"""
    __tablename__ = 'analysis_reports'
    
    id = Column(String(50), primary_key=True)
    tid = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.now)
    total_posts = Column(Integer, default=0)
    emotion_index = Column(Float, default=50.0)
    market_emotion = Column(String(20))
    bullish_ratio = Column(Float, default=0.0)
    bearish_ratio = Column(Float, default=0.0)
    neutral_ratio = Column(Float, default=0.0)
    avg_confidence = Column(Float, default=0.0)
    top_stocks = Column(Text)  # JSON string
    recommendation = Column(Text)
    
class StockMention(Base):
    """股票提及表"""
    __tablename__ = 'stock_mentions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(50), nullable=False, index=True)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100))
    market = Column(String(10))
    mention_count = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.now)
    
class UserPortfolio(Base):
    """用户持仓表"""
    __tablename__ = 'user_portfolios'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, index=True)
    stock_code = Column(String(20), nullable=False)
    stock_name = Column(String(100))
    position = Column(Integer, default=0)  # 持仓数量
    avg_cost = Column(Float, default=0.0)  # 平均成本
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now)

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = "data/ngaquant.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(exist_ok=True)
        
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        """获取数据库会话"""
        return self.Session()
    
    def save_post(self, post_data: dict):
        """保存帖子"""
        session = self.get_session()
        try:
            post = Post(**post_data)
            session.merge(post)  # merge避免重复
            session.commit()
        finally:
            session.close()
    
    def save_report(self, report_data: dict) -> str:
        """保存分析报告"""
        import uuid
        session = self.get_session()
        try:
            report_id = str(uuid.uuid4())
            report_data['id'] = report_id
            
            # 处理top_stocks为JSON
            if 'top_stocks' in report_data:
                import json
                report_data['top_stocks'] = json.dumps(report_data['top_stocks'])
            
            report = AnalysisReport(**report_data)
            session.add(report)
            session.commit()
            return report_id
        finally:
            session.close()
    
    def get_emotion_history(self, tid: str, days: int = 30) -> list:
        """获取情绪历史数据"""
        session = self.get_session()
        try:
            from datetime import timedelta
            start_date = datetime.now() - timedelta(days=days)
            
            reports = session.query(AnalysisReport).filter(
                AnalysisReport.tid == tid,
                AnalysisReport.timestamp >= start_date
            ).order_by(AnalysisReport.timestamp).all()
            
            return [{
                'timestamp': r.timestamp,
                'emotion_index': r.emotion_index,
                'market_emotion': r.market_emotion
            } for r in reports]
        finally:
            session.close()

# 全局数据库实例
db = DatabaseManager()