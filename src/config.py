"""
配置加载模块
统一管理所有配置
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class MiniMaxConfig:
    """Kimi API配置"""
    api_key: str
    base_url: str = "https://api.moonshot.cn/v1"
    model: str = "MiniMax-M2.7"

@dataclass
class FeishuConfig:
    """飞书配置"""
    webhook_url: Optional[str] = None

@dataclass
class NGAConfig:
    """NGA配置"""
    cookie: str = ""
    request_delay: int = 2
    timeout: int = 30

@dataclass
class MonitorConfig:
    """监控配置"""
    default_interval: int = 300
    emotion_change_threshold: float = 0.15
    max_threads: int = 10

@dataclass
class AnalysisConfig:
    """分析配置"""
    default_max_pages: int = 5
    max_hours: int = 72  # 只分析近 N 小时内的新回复，0 表示分析全部
    min_confidence: float = 0.6
    top_stocks_limit: int = 10

@dataclass
class BacktestConfig:
    """回测配置"""
    initial_capital: float = 100000.0
    commission_rate: float = 0.0003
    slippage: float = 0.001

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.raw_config: Dict[str, Any] = {}
        
        # 加载配置
        self._load_config()
        
        # 初始化各模块配置
        self.minimax = self._init_minimax_config()
        self.feishu = self._init_feishu_config()
        self.nga = self._init_nga_config()
        self.monitor = self._init_monitor_config()
        self.analysis = self._init_analysis_config()
        self.backtest = self._init_backtest_config()
    
    def _load_config(self):
        """加载配置文件"""
        if self.config_path.exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.raw_config = yaml.safe_load(f) or {}
        else:
            # 尝试加载example配置
            example_path = Path("config.example.yaml")
            if example_path.exists():
                with open(example_path, 'r', encoding='utf-8') as f:
                    self.raw_config = yaml.safe_load(f) or {}
            else:
                self.raw_config = {}
    
    def _init_minimax_config(self) -> MiniMaxConfig:
        """初始化MiniMax配置"""
        minimax_section = self.raw_config.get('minimax', {})
        
        # 优先从环境变量读取API Key
        api_key = os.getenv('MINIMAX_API_KEY', minimax_section.get('api_key', ''))
        
        return MiniMaxConfig(
            api_key=api_key,
            base_url=minimax_section.get('base_url', 'http://api.minimaxi.com/v1'),
            model=minimax_section.get('model', 'MiniMax-M2.7')
        )
    
    def _init_feishu_config(self) -> FeishuConfig:
        """初始化飞书配置"""
        feishu_section = self.raw_config.get('feishu', {})
        
        # 优先从环境变量读取
        webhook = os.getenv('FEISHU_WEBHOOK', feishu_section.get('webhook_url'))
        
        return FeishuConfig(webhook_url=webhook)
    
    def _init_nga_config(self) -> NGAConfig:
        """初始化NGA配置"""
        nga_section = self.raw_config.get('nga', {})
        
        return NGAConfig(
            cookie=nga_section.get('cookie', ''),
            request_delay=nga_section.get('request_delay', 2),
            timeout=nga_section.get('timeout', 30)
        )
    
    def _init_monitor_config(self) -> MonitorConfig:
        """初始化监控配置"""
        monitor_section = self.raw_config.get('monitor', {})
        
        return MonitorConfig(
            default_interval=monitor_section.get('default_interval', 300),
            emotion_change_threshold=monitor_section.get('emotion_change_threshold', 0.15),
            max_threads=monitor_section.get('max_threads', 10)
        )
    
    def _init_analysis_config(self) -> AnalysisConfig:
        """初始化分析配置"""
        analysis_section = self.raw_config.get('analysis', {})
        
        return AnalysisConfig(
            default_max_pages=analysis_section.get('default_max_pages', 5),
            max_hours=analysis_section.get('max_hours', 72),
            min_confidence=analysis_section.get('min_confidence', 0.6),
            top_stocks_limit=analysis_section.get('top_stocks_limit', 10)
        )
    
    def _init_backtest_config(self) -> BacktestConfig:
        """初始化回测配置"""
        backtest_section = self.raw_config.get('backtest', {})
        
        return BacktestConfig(
            initial_capital=backtest_section.get('initial_capital', 100000.0),
            commission_rate=backtest_section.get('commission_rate', 0.0003),
            slippage=backtest_section.get('slippage', 0.001)
        )
    
    def validate(self) -> list:
        """验证配置有效性，返回错误列表"""
        errors = []
        
        if not self.minimax.api_key or self.minimax.api_key == 'your_minimax_api_key_here':
            errors.append("MiniMax API Key未设置，请设置MINIMAX_API_KEY环境变量或更新config.yaml")
        
        return errors

# 全局配置实例
config = ConfigManager()
