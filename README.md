# NGAQuant - NGA大时代股票情绪分析器

> 基于 NGA 大时代板块帖子情绪的智能股票分析工具

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue)](Dockerfile)

## 🎯 项目概述

NGAQuant 是一个监控 NGA 大时代板块帖子情绪的量化分析工具，通过分析散户情绪来辅助投资决策。

**核心理念：**
- 散户情绪往往是反向指标（贪婪时卖出，恐惧时买入）
- 通过 NLP + LLM 分析帖子情感倾向
- 提取股票代码，生成买卖信号

## 🚀 快速开始

### 方式一：本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/noskystar/NGAQuant.git
cd NGAQuant

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp config.example.yaml config.yaml
# 编辑 config.yaml，填入你的 API Key

# 4. 运行分析
python cli.py analyze --tid 12345678
```

### 方式二：Docker 部署

```bash
# 使用 Docker Compose
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 方式三：Web 界面

```bash
streamlit run web/app.py
```

访问 http://localhost:8501

## 📊 核心功能

### 1. 数据采集 ✅
- [x] NGA 爬虫模块
- [x] HTML 解析
- [x] 增量更新机制
- [x] 错误重试

### 2. 分析处理 ✅
- [x] 情感分析（Kimi API）
- [x] 股票代码提取
- [x] 情绪指数计算
- [x] 热度统计

### 3. 用户界面 ✅
- [x] CLI 命令行工具
- [x] Web 仪表盘（Streamlit）
- [x] 情绪可视化（Plotly）
- [x] 实时报告

### 4. 数据存储 ✅
- [x] SQLite 数据库
- [x] SQLAlchemy ORM
- [x] 历史查询
- [x] 数据模型

### 5. 通知推送 ✅
- [x] 飞书机器人
- [x] Markdown 报告
- [x] 告警推送

### 6. 持仓管理 ✅
- [x] 持仓记录
- [x] 盈亏计算
- [x] 情绪结合建议

### 7. 回测系统 ✅
- [x] 策略回测
- [x] 胜率统计
- [x] 收益计算

### 8. 开发工具 ✅
- [x] 日志系统（Loguru）
- [x] 单元测试（pytest）
- [x] Docker 部署
- [x] Makefile

## 🏗️ 项目结构

```
NGAQuant/
├── README.md                 # 项目文档
├── requirements.txt          # 依赖
├── config.example.yaml       # 配置模板
├── Dockerfile               # Docker 镜像
├── docker-compose.yml       # Docker Compose
├── Makefile                 # 便捷命令
├── cli.py                   # 命令行工具
├── web/
│   └── app.py              # Web 界面
├── src/
│   ├── crawler/            # 爬虫模块
│   │   ├── __init__.py
│   │   └── nga_client.py   # NGA API/网页爬虫
│   ├── analyzer/           # 分析模块
│   │   ├── __init__.py
│   │   ├── sentiment.py    # 情感分析
│   │   └── stock_extractor.py # 股票提取
│   ├── database/           # 数据存储
│   │   ├── __init__.py
│   │   ├── models.py       # 数据模型
│   │   └── db.py           # 数据库管理
│   ├── notifier/           # 通知模块
│   │   ├── __init__.py
│   │   └── feishu.py       # 飞书推送
│   ├── portfolio/          # 持仓管理
│   │   ├── __init__.py
│   │   └── manager.py      # 持仓管理器
│   ├── monitor/            # 监控模块
│   │   ├── __init__.py
│   │   └── realtime.py     # 实时监控
│   ├── backtest/           # 回测系统
│   │   ├── __init__.py
│   │   └── engine.py       # 回测引擎
│   └── utils/              # 工具模块
│       ├── __init__.py
│       └── logger.py       # 日志配置
└── tests/                   # 测试
    ├── test_crawler.py
    └── test_stock_extractor.py
```

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| 爬虫 | Python + Playwright |
| 情感分析 | Kimi API (LLM) |
| 股票数据 | AKShare / Tushare |
| 数据库 | SQLite + SQLAlchemy |
| 后端 | Python FastAPI (CLI) |
| 前端 | Streamlit |
| 推送 | 飞书机器人 |
| 部署 | Docker + Docker Compose |
| 日志 | Loguru |
| 测试 | pytest |

## 📖 使用指南

### 环境变量配置

```bash
# Kimi API Key
export KIMI_API_KEY="your_api_key"

# 飞书 Webhook（可选）
export FEISHU_WEBHOOK="https://open.feishu.cn/..."
```

### CLI 命令

```bash
# 分析指定帖子
python cli.py analyze --tid 12345678 --max-pages 5

# 监控模式（开发中）
python cli.py monitor --tid 12345678 --interval 300
```

### Web 界面功能

- 📊 情绪指数仪表盘
- 📈 情感分布饼图
- 🔥 热门股票列表
- 💡 投资建议展示
- 📚 历史记录查询

## 🛣️ 路线图

### Phase 1: MVP ✅ (已完成)
- [x] 基础爬虫
- [x] 情感分析
- [x] CLI工具
- [x] Web界面
- [x] 数据存储
- [x] 通知推送
- [x] 持仓管理
- [x] 回测系统

### Phase 2: 增强 ✅ (已完成)
- [x] 配置管理（YAML + 环境变量）
- [x] 实时监控（情绪告警）
- [x] 爬虫重试机制
- [x] 股票字典扩展（115只+）
- [x] 功能测试脚本

### Phase 3: 智能 (规划中)
- [ ] 自动交易对接
- [ ] 机器学习模型
- [ ] 策略优化
- [ ] 社区功能

## 📈 效果验证

通过历史数据回测，验证策略有效性：
- 情绪指标 vs 股价走势
- 信号准确率
- 收益率统计

## 🌐 部署方案

### 方案 1：Render（推荐）
免费部署 Web 界面：
1. 连接 GitHub 仓库
2. 自动识别 Dockerfile
3. 免费 HTTPS 域名

### 方案 2：Railway
免费部署：
- 每月 500 小时免费额度
- 自动 CI/CD
- 简单配置

### 方案 3：自托管
使用 Docker Compose：
```bash
docker-compose up -d
```

## 📝 开发进度

**当前状态：Phase 1 完成 ✅**

- 总代码量：约 4000 行
- 模块数量：8 个核心模块
- 测试覆盖：核心功能
- 部署方式：Docker + 本地

## ⚠️ 免责声明

本工具仅供学习研究，不构成投资建议。
股市有风险，投资需谨慎。

## 🤝 贡献

欢迎提交 Issue 和 PR！

## 📝 License

MIT License
