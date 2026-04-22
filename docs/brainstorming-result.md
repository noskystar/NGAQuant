# NGAQuant 智能选股系统 — 设计方案

> 方案：B（情绪 + 价格双因子）
> 版本：v1.0
> 日期：2026-04-22

---

## 1. 项目愿景和目标

### 1.1 愿景
将 NGAQuant 从单一的"散户情绪分析工具"升级为**情绪驱动型量化选股系统**。
核心投资假设：
- **散户情绪是反向指标** —— 极端贪婪时市场短期见顶，极端恐惧时孕育反弹
- **纯情绪数据不够，需要股价验证** —— 情绪极值必须得到价格技术面确认，才能过滤假信号、降低噪音

### 1.2 目标
| 目标 | 说明 |
|------|------|
| 短线选股 | 基于当日情绪极值 + 价格技术形态，生成 1-3 天持仓的买卖信号 |
| 中线布局 | 基于情绪趋势变化 + 价格趋势确认，生成 1-4 周持仓的布局信号 |
| 信号可验证 | 每个信号有明确入场/出场条件，系统自动跟踪绩效（胜率、盈亏、最大回撤） |
| 多终端覆盖 | CLI + Web UI 同时支持，定时任务自动运行 |

---

## 2. 推荐算法设计（短线 + 中线）

### 2.1 双因子模型框架

```
综合信号分 = α × 反向情绪分 + β × 价格因子分
```

- **反向情绪分** = 100 − 情绪指数(EF)（情绪越恐惧，反向分越高，越看涨）
- **价格因子分** = 趋势分 + 动量分 + 量价分（0-100）
- 权重：短线 α=0.45, β=0.55；中线 α=0.55, β=0.45（中线更重视情绪趋势）

### 2.2 情绪因子 (Emotion Factor, EF)

复用现有 `SentimentAggregator`，从 NGA 帖子分析得到：
- `emotion_index`: 0-100（现有）
- `bullish_ratio` / `bearish_ratio`: 看涨/看跌比例（现有）
- **新增** `emotion_trend_3d`: 近 3 次分析的情绪指数移动平均（用于中线）

### 2.3 价格因子 (Price Factor, PF)

通过 akshare 获取股票日线数据，计算三项子指标：

| 子指标 | 权重 | 计算方式 |
|--------|------|----------|
| 趋势分 | 0-40 | 收盘价 vs MA5/MA10/MA20 位置关系；多头排列 40 分，空头排列 0 分 |
| 动量分 | 0-30 | RSI(14)：超卖区(0-30)→30分，中性区→15分，超买区(70-100)→0分 |
| 量价分 | 0-30 | 当日成交量 vs 20 日均量；放量上涨 30 分，缩量下跌 20 分，放量下跌 0 分 |

### 2.4 短线策略（持仓 1-3 天）

**买入信号（BUY）** 需同时满足：
1. 反向情绪分 ≥ 70（情绪极度恐惧或偏恐惧）
2. 价格因子分 ≥ 60（技术面不处于下跌趋势）
3. 当日涨跌幅 < +5%（避免追高风险）
4. 该股票在近 3 日情绪分析中被提及 ≥ 3 次（保证关注度）

**卖出/回避信号（SELL）** 需同时满足：
1. 反向情绪分 ≤ 30（情绪极度贪婪）
2. 价格因子分 ≤ 40（技术面滞涨或走弱）
3. 当日涨跌幅 > -3%（避免杀跌在底部）

**信号强度等级**：
- `STRONG`: 综合分 ≥ 85
- `MODERATE`: 综合分 70-85
- `WEAK`: 综合分 60-70（仅观察，不入池）

### 2.5 中线策略（持仓 1-4 周）

**布局信号（ACCUMULATE）** 需同时满足：
1. 情绪 3 日均线从恐惧区（<35）回升，且最新情绪指数 > 3 日均线（趋势转折）
2. 价格突破 MA20 或 MA20 拐头向上
3. RSI 从超卖区回升至 40 以上
4. 成交量温和放大（> 20 日均量 1.2 倍）

**减仓信号（REDUCE）** 需同时满足：
1. 情绪 3 日均线从贪婪区（>65）回落
2. 价格跌破 MA10 或出现放量阴线
3. RSI 从超买区回落至 60 以下

### 2.6 个股信号生成流程

```
1. 从帖子分析获取热门股票列表（Top 10-20）
2. 对每只股票调用 akshare 获取近 60 日日线数据
3. 计算技术指标 → 价格因子分
4. 结合该帖子/全局情绪指数 → 反向情绪分
5. 按策略规则生成信号（BUY/SELL/HOLD/ACCUMULATE/REDUCE）
6. 按综合分排序，取前 5 作为推荐
```

---

## 3. 数据模型改动（新增表 / 字段）

### 3.1 新增表

#### `stock_prices` — 股票价格日线数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer, PK, autoincrement | |
| stock_code | String(20), index | 股票代码 |
| stock_name | String(100) | 股票名称 |
| trade_date | Date | 交易日期 |
| open | Float | 开盘价 |
| high | Float | 最高价 |
| low | Float | 最低价 |
| close | Float | 收盘价 |
| volume | BigInteger | 成交量 |
| change_pct | Float | 涨跌幅 % |
| ma5 | Float | 5日均线 |
| ma10 | Float | 10日均线 |
| ma20 | Float | 20日均线 |
| rsi_14 | Float | RSI(14) |
| macd_dif | Float | MACD DIF |
| macd_dea | Float | MACD DEA |
| macd_bar | Float | MACD 柱状线 |
| created_at | DateTime | 记录创建时间 |

**索引**: `(stock_code, trade_date)` 联合唯一

#### `stock_signals` — 股票推荐信号

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(50), PK | UUID |
| stock_code | String(20), index | 股票代码 |
| stock_name | String(100) | 股票名称 |
| signal_type | String(20) | BUY / SELL / HOLD / ACCUMULATE / REDUCE |
| strategy | String(20) | SHORT / MID |
| emotion_factor | Float | 情绪指数 (0-100) |
| reverse_emotion_score | Float | 反向情绪分 (0-100) |
| price_factor | Float | 价格因子分 (0-100) |
| composite_score | Float | 综合信号分 (0-100) |
| strength | String(20) | STRONG / MODERATE / WEAK |
| reason | Text | 信号生成理由（JSON） |
| source_tid | String(20) | 来源帖子ID |
| generated_at | DateTime | 生成时间 |
| valid_until | DateTime | 信号有效期（短线+3天，中线+28天） |
| status | String(20) | ACTIVE / HIT / EXPIRED / STOPPED |
| hit_price | Float | 触发/入场价格 |
| exit_price | Float | 出场价格 |
| return_pct | Float | 实际收益率 |

**索引**: `(stock_code, status)`, `(generated_at, strategy)`

#### `signal_performance` — 信号绩效追踪

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer, PK, autoincrement | |
| signal_id | String(50), FK | 关联 stock_signals |
| stock_code | String(20) | |
| entry_price | Float | 入场价 |
| exit_price | Float | 出场价 |
| hold_days | Integer | 持有天数 |
| return_pct | Float | 收益率 |
| max_drawdown | Float | 持有期内最大回撤 |
| hit_at | DateTime | 信号触发时间 |
| exited_at | DateTime | 信号结束时间 |
| exit_reason | String(50) | TP(止盈) / SL(止损) / EXPIRED(到期) / MANUAL |

### 3.2 现有表新增字段

#### `AnalysisReport`
| 字段 | 类型 | 说明 |
|------|------|------|
| composite_index | Float | 情绪+价格综合指数（若当时有价格数据） |
| strategy_signals | Text | 该次分析生成的信号列表（JSON） |

---

## 4. 新增模块列表

```
src/
├── prices/                  # 新增：价格数据获取与因子计算
│   ├── __init__.py
│   ├── fetcher.py          # akshare 日线/实时数据获取
│   ├── indicators.py       # 技术指标计算（MA, RSI, MACD, 成交量）
│   └── factor.py           # 价格因子评分（趋势/动量/量价）
│
├── recommender/             # 新增：推荐引擎
│   ├── __init__.py
│   ├── engine.py           # 双因子融合算法主入口
│   ├── strategies.py       # 短线/中线策略规则定义
│   ├── scorer.py           # 个股综合打分排序
│   └── models.py           # Signal, SignalType, StrategyType 等 dataclass
│
├── signals/                 # 新增：信号生命周期管理
│   ├── __init__.py
│   ├── manager.py          # 信号生成、查询、过期处理
│   ├── validator.py        # 信号命中验证（每日收盘后对比价格）
│   └── performance.py      # 绩效统计（胜率、平均收益、最大回撤）
│
├── scheduler/               # 新增：定时任务
│   ├── __init__.py
│   ├── jobs.py             # APScheduler 任务定义
│   └── runner.py           # 任务调度器启动入口
│
└── database/
    └── db.py               # 扩展：新增 price/signal 相关 CRUD

web/
├── app.py                  # 改造：多页导航入口 (st.navigation)
├── pages/                  # 新增：多页面目录
│   ├── __init__.py
│   ├── analyze.py          # 帖子分析页（现有功能迁移）
│   ├── dashboard.py        # 新增：首页仪表盘（情绪+今日信号）
│   ├── recommendations.py  # 新增：推荐中心（短线/中线信号列表）
│   ├── stock_detail.py     # 新增：个股详情（价格+情绪+历史信号）
│   ├── backtest.py         # 新增：回测结果展示
│   └── settings.py         # 新增：策略参数配置
```

---

## 5. Web UI 改版设计

### 5.1 架构改造

从单页 Streamlit 应用改造为**多页应用**（`st.navigation`）：

```python
pg = st.navigation([
    st.Page("pages/dashboard.py", title="仪表盘", icon="📊"),
    st.Page("pages/analyze.py", title="帖子分析", icon="🔍"),
    st.Page("pages/recommendations.py", title="推荐中心", icon="🎯"),
    st.Page("pages/stock_detail.py", title="个股追踪", icon="📈"),
    st.Page("pages/backtest.py", title="回测验证", icon="🧪"),
    st.Page("pages/settings.py", title="设置", icon="⚙️"),
])
```

### 5.2 各页面设计

#### 📊 仪表盘 (Dashboard)
- **顶部 KPI 行**: 今日情绪指数 / 活跃推荐信号数 / 本月胜率 / 最新信号综合分最高股
- **情绪仪表盘**: 现有 gauge 图（复用）
- **今日推荐卡片**: 横向排列 Top 3 信号卡片（股票名 + 信号类型 + 综合分 + 有效期倒计时）
- **情绪-价格相关性图**: 近 30 日情绪指数 vs 上证指数走势叠加图

#### 🔍 帖子分析 (Analyze)
- 现有分析功能完整迁移
- **新增**: 分析完成后在结果页展示"基于本帖的推荐信号"（热门股票的信号卡片）

#### 🎯 推荐中心 (Recommendations)
- **策略切换 Tab**: 短线 / 中线
- **信号列表**: 每行一张卡片
  - 左：股票名称 + 代码 + 市场标签
  - 中：信号徽章（BUY/SELL 彩色标签）+ 强度（STRONG 火焰图标）
  - 右：三列小指标（情绪分/价格分/综合分 进度条）
  - 底部：理由摘要 + 生成时间 + 有效期
- **点击展开**: 详细理由 JSON + 近 20 日 K 线迷你图（Plotly Candlestick）
- **排序**: 按综合分 / 按生成时间 / 按有效期

#### 📈 个股追踪 (Stock Detail)
- **搜索框**: 输入股票名/代码跳转
- **价格走势图**: K 线 + MA5/MA10/MA20 + 成交量（下方副图）
- **情绪关联面板**: 该股票被提及的历史情绪分析时间线
- **历史信号表**: 该股票过往所有信号及实际绩效

#### 🧪 回测验证 (Backtest)
- **参数区**: 策略选择 / 回测起止日期 / 初始资金 / 止盈止损 %
- **结果区**: 
  - 收益曲线图（vs 沪深300基准）
  - KPI 卡片：总收益率 / 年化收益 / 胜率 / 最大回撤 / 夏普比率
  - 交易记录表格：每笔信号的进出时间、价格、盈亏

#### ⚙️ 设置 (Settings)
- API Key 配置（现有）
- **新增 策略参数**: 短线/中线权重滑块、情绪阈值、RSI 参数、止盈止损比例
- **新增 定时任务**: 启用/禁用各任务、修改执行时间

---

## 6. CLI 命令设计

在现有 `cli.py` 基础上新增以下子命令：

### 6.1 价格数据命令

```bash
# 更新所有热门股票的价格数据
python cli.py price update --all

# 更新单只股票
python cli.py price update --code 600519 --days 60

# 查看某股票最新价格和技术指标
python cli.py price show --code 600519
```

### 6.2 推荐命令

```bash
# 生成短线推荐（基于最新情绪和价格数据）
python cli.py recommend --strategy short --limit 10

# 生成中线推荐
python cli.py recommend --strategy mid --limit 10

# 基于指定帖子生成推荐
python cli.py recommend --tid 25914502 --strategy short

# 输出格式：默认表格 / JSON
python cli.py recommend --strategy short --format json
```

输出示例：
```
🎯 短线推荐信号（生成于 2026-04-22 15:35）

排名  股票        信号    强度      情绪分  价格分  综合分  有效期
----  ----------  ------  --------  ------  ------  ------  ----------
1     贵州茅台    BUY     STRONG    72.5    68.0    85.2    2026-04-25
2     比亚迪      BUY     MODERATE  65.0    70.5    78.3    2026-04-25
3     宁德时代    HOLD    -         48.0    52.0    50.0    -
```

### 6.3 信号管理命令

```bash
# 列出当前活跃信号
python cli.py signals list --strategy short --status active

# 验证信号表现（对比今日收盘价检查是否触发）
python cli.py signals validate

# 查看某信号详情
python cli.py signals show --id <signal_id>

# 查看历史信号绩效统计
python cli.py signals stats --strategy short --days 30
```

### 6.4 回测命令

```bash
# 运行回测
python cli.py backtest --strategy short --start 2026-01-01 --end 2026-04-22 --capital 100000

# 快速回测（近 N 天）
python cli.py backtest --strategy short --days 30
```

### 6.5 监控增强

```bash
# 启动推荐监控（定时分析并推送）
python cli.py monitor --mode recommendation --interval 300

# 启动完整监控（情绪+价格+推荐）
python cli.py monitor --mode full --interval 300
```

---

## 7. 定时任务设计

使用 **APScheduler** 作为定时任务框架，任务配置写入 `config.yaml`。

### 7.1 任务清单

| 任务名 | 调度规则 | 说明 |
|--------|----------|------|
| `update_prices_daily` | 工作日 15:35, 20:00 | 获取当日所有关注股票收盘价，计算技术指标 |
| `crawl_and_analyze` | 每 5 分钟 | 爬取关注列表帖子新页，情感分析，更新情绪指数 |
| `generate_signals` | 工作日 9:00, 15:30 | 基于最新情绪+价格数据生成短线/中线信号 |
| `validate_signals` | 工作日 15:35 | 验证活跃信号是否命中，更新绩效数据 |
| `cleanup_expired` | 每日 0:00 | 清理过期信号，归档历史数据 |
| `feishu_push_morning` | 工作日 9:10 | 飞书推送今日早盘推荐 |
| `feishu_push_close` | 工作日 15:40 | 飞书推送收盘总结 + 信号更新 |

### 7.2 任务执行流程

#### update_prices_daily
```
1. 从 stock_mentions / watchlist 获取需要跟踪的股票代码列表
2. 调用 akshare 批量获取前一日日线数据
3. 计算 MA5/MA10/MA20, RSI(14), MACD
4. 写入 stock_prices 表（merge 避免重复）
```

#### crawl_and_analyze
```
1. 遍历 watchlist.json 中的帖子 ID
2. 对每个 tid：爬取最新页 → 提取股票 → 情感分析
3. 保存到 history 和 AnalysisReport
4. 如情绪指数变化 > 阈值，触发飞书告警
```

#### generate_signals
```
1. 获取最新情绪指数（全局或各帖子）
2. 获取近 3 日情绪趋势
3. 从 stock_prices 读取最新技术指标
4. 调用 RecommenderEngine 生成信号
5. 写入 stock_signals 表
6. 如 STRONG 信号数量 > 0，触发飞书推荐推送
```

#### validate_signals
```
1. 查询 status=ACTIVE 的信号
2. 对比当日收盘价：
   - BUY 信号：若收盘价 >= 当日开盘价（已上涨）→ 标记 HIT，记录 entry_price
   - SELL 信号：若收盘价 <= 当日开盘价 → 标记 HIT
3. 检查是否过期（valid_until < now）→ 标记 EXPIRED
4. 对已 HIT 的信号，检查止盈/止损条件：
   - 止盈：从 entry_price 上涨 +10%（短线）/ +20%（中线）
   - 止损：从 entry_price 下跌 -5%（短线）/ -10%（中线）
   - 触发则标记 STOPPED，记录 exit_price 和 return_pct
```

### 7.3 配置示例

```yaml
scheduler:
  enabled: true
  timezone: "Asia/Shanghai"
  jobs:
    update_prices:
      trigger: "cron"
      hour: "15,20"
      minute: "35,00"
      day_of_week: "mon-fri"
    generate_signals:
      trigger: "cron"
      hour: "9,15"
      minute: "0,30"
      day_of_week: "mon-fri"
    validate_signals:
      trigger: "cron"
      hour: "15"
      minute: "35"
      day_of_week: "mon-fri"
    crawl:
      trigger: "interval"
      minutes: 5
```

---

## 8. 分阶段实现计划

### Phase 1: 价格数据基础设施（Week 1，Days 1-3）

**目标**: 建立股票价格获取、存储、指标计算能力

- [ ] `src/prices/fetcher.py` — akshare 日线数据获取，支持 A股/港股/美股/指数
- [ ] `src/prices/indicators.py` — MA, RSI, MACD 计算（使用 pandas/ta-lib 或纯 pandas）
- [ ] `src/prices/factor.py` — 价格因子评分（趋势/动量/量价）
- [ ] 扩展 `src/database/db.py` — `stock_prices` 表的 CRUD
- [ ] CLI: `python cli.py price update/show`
- [ ] 测试：验证指标计算结果与主流软件一致

### Phase 2: 推荐算法核心（Week 1-2，Days 4-7）

**目标**: 实现双因子融合算法，能生成可解释的信号

- [ ] `src/recommender/models.py` — Signal dataclass, SignalType, StrategyType
- [ ] `src/recommender/strategies.py` — 短线/中线策略规则实现
- [ ] `src/recommender/scorer.py` — 个股打分排序
- [ ] `src/recommender/engine.py` — 主引擎：输入帖子分析结果 + 价格数据 → 输出信号列表
- [ ] `src/signals/manager.py` — 信号持久化、查询、过期管理
- [ ] 扩展 `src/database/db.py` — `stock_signals` 表的 CRUD
- [ ] CLI: `python cli.py recommend`
- [ ] 测试：用历史数据验证信号生成逻辑正确

### Phase 3: Web UI 多页改版（Week 2-3，Days 8-12）

**目标**: 从单页改为多页，新增推荐中心、个股追踪、回测页面

- [ ] 改造 `web/app.py` — `st.navigation` 多页入口
- [ ] `web/pages/analyze.py` — 迁移现有分析页面
- [ ] `web/pages/dashboard.py` — 首页仪表盘（情绪 + 今日 Top 信号）
- [ ] `web/pages/recommendations.py` — 推荐中心（短线/中线 Tab + 信号卡片 + K线迷你图）
- [ ] `web/pages/stock_detail.py` — 个股详情（K线+情绪关联+历史信号）
- [ ] `web/pages/backtest.py` — 回测参数 + 结果展示
- [ ] `web/pages/settings.py` — 策略参数可视化配置
- [ ] 测试：各页面交互正常，数据展示正确

### Phase 4: 信号验证与回测增强（Week 3，Days 13-15）

**目标**: 信号可被验证，系统能统计真实绩效

- [ ] `src/signals/validator.py` — 每日收盘后验证活跃信号
- [ ] `src/signals/performance.py` — 胜率、平均收益、最大回撤统计
- [ ] `src/backtest/engine.py` — 增强回测引擎（使用真实历史信号和价格数据）
- [ ] `src/database/db.py` — `signal_performance` 表 CRUD
- [ ] CLI: `python cli.py signals validate/stats` + `python cli.py backtest`
- [ ] 测试：模拟历史数据验证回测逻辑

### Phase 5: 定时任务与自动化推送（Week 3-4，Days 16-18）

**目标**: 系统全自动运行，每日自动推送推荐

- [ ] `src/scheduler/jobs.py` — 所有定时任务定义
- [ ] `src/scheduler/runner.py` — APScheduler 启动器
- [ ] 增强 `src/notifier/feishu.py` — 新增推荐推送模板、收盘总结模板
- [ ] `config.yaml` 新增 scheduler 配置段
- [ ] CLI: `python cli.py monitor --mode recommendation`
- [ ] Dockerfile / docker-compose.yml 更新（支持后台 scheduler 进程）
- [ ] 测试：模拟定时任务执行，验证推送内容格式

### Phase 6: 集成测试与优化（Week 4，Days 19-21）

**目标**: 端到端验证，修复问题，优化性能

- [ ] 端到端测试：完整跑通"爬帖 → 分析 → 取价 → 生成信号 → 验证 → 推送"链路
- [ ] 性能优化：akshare 批量请求、数据库查询优化
- [ ] 错误处理：网络失败、数据缺失时的降级策略
- [ ] 文档更新：README、CLI help、Web 页面内帮助
- [ ] 代码审查：清理 TODO，确保无硬编码，配置外置

---

## 附录：技术选型说明

| 组件 | 选型 | 理由 |
|------|------|------|
| 价格数据源 | akshare | 项目已有依赖，免费，A股数据完整 |
| 指标计算 | pandas + numpy | 轻量，无需额外依赖 ta-lib |
| 定时任务 | APScheduler | Python 原生，功能完善，配置灵活 |
| Web 框架 | Streamlit (多页) | 保持现有技术栈，迁移成本低 |
| 数据库 | SQLite (继续) | 当前规模足够，后期可迁移 PostgreSQL |
| 图表 | Plotly | 现有使用，支持 K 线、交互丰富 |

---

## 附录：风险提示

1. **数据延迟**: akshare 免费数据有 15 分钟延迟，短线信号仅适合 T+1 复盘和次日计划，不适合实时盯盘
2. **样本偏差**: NGA 大时代板块用户不能代表全市场散户，情绪指标存在板块偏向
3. **过拟合风险**: 策略参数需经过至少 6 个月历史数据验证，避免过度优化
4. **免责声明**: 所有信号仅用于学习研究，不构成投资建议
