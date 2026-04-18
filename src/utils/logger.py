# 日志配置
from loguru import logger
import sys
from pathlib import Path

# 创建日志目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 配置日志
logger.remove()  # 移除默认配置

# 控制台输出
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# 文件输出 - 按天轮转
logger.add(
    log_dir / "ngaquant_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # 每天午夜轮转
    retention="30 days",  # 保留30天
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

# 错误日志单独记录
logger.add(
    log_dir / "error_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="30 days",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR"
)

# 导出logger
__all__ = ['logger']