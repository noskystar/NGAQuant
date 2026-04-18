# NGAQuant - NGA大时代股票情绪分析器

> 基于 NGA 大时代板块帖子情绪的智能股票分析工具

## 🎯 产品概述

NGAQuant 是一个监控 NGA 大时代板块帖子情绪的量化分析工具，通过分析散户情绪来辅助投资决策。

**核心理念：**
- 散户情绪往往是反向指标（贪婪时卖出，恐惧时买入）
- 通过 NLP + LLM 分析帖子情感倾向
- 提取股票代码，生成买卖信号

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                     NGAQuant 架构                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │  数据采集层  │ →  │  分析处理层  │ →  │  决策输出层  │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│                                                          │
│  • NGA 爬虫          • 情感分析          • 交易信号      │
│  • 帖子存储          • 股票提取          • 风险评估      │
│  • 增量更新          • 热度计算          • 推送通知      │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## 📁 项目结构

```
NGAQuant/
├── README.md                 # 项目文档
├── requirements.txt          # 依赖
├── config.yaml              # 配置文件
├── src/
│   ├── __init__.py
│   ├── crawler/             # 爬虫模块
│   │   ├── __init__.py
│   │   ├── nga_client.py    # NGA API/网页爬虫
│   │   └── parser.py        # HTML解析
│   ├── analyzer/            # 分析模块
│   │   ├── __init__.py
│   │   ├── sentiment.py     # 情感分析
│   │   ├── stock_extractor.py # 股票提取
│   │   └── llm_client.py    # LLM接口
│   ├── database/            # 数据存储
│   │   ├── __init__.py
│   │   └── models.py        # 数据模型
│   ├── signals/             # 信号生成
│   │   ├── __init__.py
│   │   └── generator.py     # 交易信号
│   └── notifier/            # 通知模块
│       ├── __init__.py
│       └── feishu.py        # 飞书推送
├── cli.py                   # 命令行工具
├── web/                     # Web界面 (Streamlit)
│   └── app.py
└── tests/                   # 测试
    └── test_analyzer.py
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制 `config.example.yaml` 为 `config.yaml`，填写：
- NGA Cookie（用于访问大时代板块）
- Kimi API Key
- 飞书 Webhook（可选）

### 3. 运行

```bash
# 分析指定帖子
python cli.py analyze --url "https://bbs.nga.cn/read.php?tid=XXXXX"

# 监控模式（定时更新）
python cli.py monitor --tid XXXXX --interval 300

# Web界面
streamlit run web/app.py
```

## 📊 核心功能

### 1. 数据采集
- 抓取指定 NGA 帖子内容
- 提取楼主发言和回复
- 增量更新机制

### 2. 情感分析
- 使用 LLM 分析情感倾向（看涨/看跌/中性）
- 识别情绪强度
- 统计情绪分布

### 3. 股票提取
- 从文本中提取股票名称/代码
- 映射到真实股票代码
- 计算提及热度

### 4. 交易信号
- 生成买卖建议
- 风险评估
- 持仓分析

### 5. 通知推送
- 飞书机器人推送
- 定时报告
- 异常提醒

## 🛣️ 路线图

### Phase 1: MVP (1周)
- [x] 基础爬虫
- [x] 情感分析
- [x] CLI工具

### Phase 2: 增强 (2周)
- [ ] Web界面
- [ ] 多帖子监控
- [ ] 回测系统

### Phase 3: 智能 (1月)
- [ ] 自动交易对接
- [ ] 策略优化
- [ ] 社区功能

## 📈 效果验证

通过历史数据回测，验证策略有效性：
- 情绪指标 vs 股价走势
- 信号准确率
- 收益率统计

## ⚠️ 免责声明

本工具仅供学习研究，不构成投资建议。
股市有风险，投资需谨慎。

## 📝 License

MIT License
