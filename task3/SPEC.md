# SPEC — 均线交叉策略多标的回测

> 量化课程项目：编程实现均线交叉（MA Crossover）交易策略，对多个 A 股标的进行回测，
> 评估最大回撤（MDD）、夏普比率（Sharpe Ratio）、累计回报（Cumulative Return）三项核心指标。

---

## 1. 项目目标

| 维度 | 说明 |
|------|------|
| **策略** | 双均线交叉策略：短周期均线上穿长周期均线 → 金叉买入；下穿 → 死叉卖出 |
| **市场** | A 股（沪深），日 K 线数据 |
| **标的** | 多只代表性股票（跨行业），支持可配置扩展 |
| **回测区间** | 默认近 2 年（约 480 个交易日），可参数化 |
| **核心交付** | ① 策略/回测引擎源码 ② 多标的对比表 ③ 权益曲线对比图 ④ 回测报告 |

本 Spec 对接既有项目资产：复用 `technical_indicators.py` 的数据加载约定（`date,open,high,low,close,volume,amount` 列结构）与 matplotlib 中文字体方案，新增回测能力。

---

## 2. 策略设计

### 2.1 核心逻辑

均线交叉策略属于趋势跟踪类策略，基于「短周期均线与长周期均线的相对位置判断趋势方向」。

- **金叉（Golden Cross）**：短期均线（SMA_short）由下向上穿越长期均线（SMA_long）→ 产生 **买入** 信号，满仓建仓。
- **死叉（Death Cross）**：短期均线由上向下穿越长期均线 → 产生 **卖出** 信号，清仓离场。
- 其余时间 **持仓不变**（已持仓则持有，空仓则继续空仓）。

### 2.2 均线类型

支持两种均线计算方式（通过参数切换）：

| 类型 | 公式 | 特点 |
|------|------|------|
| **SMA** 简单移动平均 | `SMA[t] = mean(Close[t-N+1 : t+1])` | 等权，信号稳定，默认 |
| **EMA** 指数移动平均 | `EMA[t] = α·Close[t] + (1-α)·EMA[t-1]`, `α=2/(N+1)` | 近期权重高，反应灵敏 |

### 2.3 默认参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `short_window` | 5 | 短周期窗口 |
| `long_window` | 20 | 长周期窗口 |
| `ma_type` | `sma` | 均线类型：`sma` / `ema` |
| `initial_capital` | 100000 | 初始资金（元） |
| `commission_rate` | 0.0003 | 双边佣金费率（万三） |
| `slippage` | 0.001 | 滑点费率（千一） |
| `risk_free_rate` | 0.0 | 无风险利率（年化），夏普比率用，默认 0 |

> 参数说明：A 股佣金一般为万 2.5 ~ 万 3（双边），此处取万三偏保守；滑点千一为常见经验值。
> `short_window < long_window` 为硬约束，程序需校验。

### 2.4 信号生成（伪代码）

```
df['ma_short'] = SMA(close, short_window)
df['ma_long']  = SMA(close, long_window)

# 金叉：今日短>长 且 昨日短<=长
golden_cross = (ma_short > ma_long) & (ma_short.shift(1) <= ma_long.shift(1))
# 死叉：今日短<长 且 昨日短>=长
death_cross  = (ma_short < ma_long) & (ma_short.shift(1) >= ma_long.shift(1))

# 持仓状态：金叉后置 1（满仓），死叉后置 0（空仓），warmup 期前置 0
position = 0
for t in range(len(df)):
    if t < long_window:           # warmup：均线尚未就绪
        position[t] = 0
    elif golden_cross[t]:
        position[t] = 1
    elif death_cross[t]:
        position[t] = 0
    else:
        position[t] = position[t-1]   # 维持前一日仓位
```

### 2.5 交易执行假设

- **执行价格**：信号日 **次日开盘价** 成交（避免未来函数 / look-ahead bias）。
- **仓位**：满仓买入（`position ∈ {0, 1}`），不做仓位管理与杠杆。
- **交易单位**：按整手（100 股）取整买入，剩余资金留作现金。
- **手续费**：买入时扣除 `commission_rate + slippage`，卖出时同样扣除。
- **无做空**：A 股为 T+1 且融券受限，本策略仅做多。

---

## 3. 数据需求

### 3.1 数据来源

通过 Tushare MCP 接口（`mcp__tushareMcp__daily`）获取前复权日 K 线，与既有 `埃斯顿_002747/data.csv` 同源同格式。

### 3.2 默认标的池

跨行业选取 5 只代表性股票，保证风格差异以观察策略普适性：

| 代码 | 名称 | 行业 | 选择理由 |
|------|------|------|----------|
| 002747.SZ | 埃斯顿 | 机器人 | 已有数据，趋势性较强 |
| 600519.SH | 贵州茅台 | 白酒 | 大盘价值，低波动 |
| 300750.SZ | 宁德时代 | 新能源 | 高波动成长 |
| 600036.SH | 招商银行 | 银行 | 蓝筹，震荡市代表 |
| 002594.SZ | 比亚迪 | 新能源车 | 成长白马 |

> 标的池存于配置，可自由增删。程序对每只标的独立回测，再做横向对比。

### 3.3 数据规格

- 列：`date, open, high, low, close, volume, amount`（与既有项目一致）
- `date`：ISO 日期，升序排列
- `amount` 单位：元（Tushare 千元需 ×1000 转换）
- 数据质量：自动校验缺失值、价格逻辑（`low ≤ open,close ≤ high`）、日期连续性

---

## 4. 回测引擎设计

### 4.1 评估指标定义

设策略每日收益率为 `r_t`，权益曲线为 `equity_t`，共 `N` 个交易日。

#### ① 累计回报（Cumulative Return）

```
CumulativeReturn = (equity_final / initial_capital) - 1
```

同时计算 **基准累计回报**（买入持有）作为对照：
```
BenchmarkReturn = (close_final / close_first) - 1
```

#### ② 夏普比率（Sharpe Ratio）

年化夏普比率，`r_f` 为无风险年化利率（默认 0）：

```
daily_rf      = (1 + risk_free_rate) ** (1/252) - 1
excess_return = r_t - daily_rf
Sharpe = mean(excess_return) / std(excess_return) × sqrt(252)
```

> 当 `std == 0` 时返回 0，避免除零。

#### ③ 最大回撤（Maximum Drawdown, MDD）

```
cumulative_max = equity.cummax()
drawdown       = (equity - cumulative_max) / cumulative_max
MDD            = abs(min(drawdown))         # 取绝对值，正值表示回撤幅度
```

#### ④ 辅助指标（自动附带）

| 指标 | 公式 | 用途 |
|------|------|------|
| 年化收益率 | `(1+CumReturn) ** (252/N) - 1` | 标准化对比 |
| 年化波动率 | `std(r_t) × sqrt(252)` | 风险度量 |
| 交易次数 | 金叉+死叉次数合计 | 检验过度交易 |
| 胜率 | 盈利交易数 / 总交易数 | 信号质量 |
| Calmar 比率 | 年化收益率 / MDD | 风险调整收益 |

### 4.2 模块划分

```
量化课程/
├── 埃斯顿_002747/              # 既有数据
├── technical_indicators.py     # 既有指标脚本
├── ma_strategy.py              # 【新】均线交叉策略：信号生成
├── backtest_engine.py         # 【新】回测引擎：撮合 + 指标计算
├── run_backtest.py            # 【新】批量回测主程序 + 可视化
├── backtest_data/             # 【新】多标的数据目录
│   ├── 002747.csv
│   ├── 600519.csv
│   └── ...
├── backtest_results/          # 【新】输出目录
│   ├── backtest_report.html  # 对比仪表盘
│   ├── comparison_table.csv   # 指标对比表
│   └── equity_curves.png      # 权益曲线对比图
└── SPEC.md                    # 本文件
```

### 4.3 核心类/函数接口

```python
# ma_strategy.py
class MovingAverageCrossover:
    def __init__(self, short_window=5, long_window=20, ma_type="sma"): ...
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """返回 df 附加列: ma_short, ma_long, signal(1/-1/0), position"""

# backtest_engine.py
class BacktestEngine:
    def __init__(self, initial_capital=100000, commission_rate=0.0003,
                 slippage=0.001, risk_free_rate=0.0): ...
    def run(self, df: pd.DataFrame, signals: pd.DataFrame) -> dict:
        """返回 {equity_curve, trades, metrics}"""
    def compute_metrics(self, equity: pd.Series, trades: list) -> dict:
        """返回 {cumulative_return, sharpe, mdd, annual_return, ...}"""

# run_backtest.py
def load_or_fetch(ticker: str, start: str, end: str) -> pd.DataFrame: ...
def run_batch(tickers: list, params: dict) -> pd.DataFrame: ...
def plot_equity_curves(results: dict, output: str): ...
def build_report(results: dict, output: str): ...
```

---

## 5. 输出物

### 5.1 对比表（comparison_table.csv）

| 标的 | 策略累计回报 | 基准累计回报 | 夏普比率 | 最大回撤 | 年化收益 | 年化波动 | 交易次数 | 胜率 | Calmar |
|------|------------|------------|---------|---------|---------|---------|---------|------|--------|

### 5.2 权益曲线对比图（equity_curves.png）

- 横轴：日期；纵轴：归一化净值（起点=1.0）
- 每只标的一条策略曲线 + 一条半透明基准曲线
- 红涨绿跌（A 股惯例）标注买卖点（单标的详情图）
- 中文字体自动适配

### 5.3 交互式回测报告（backtest_report.html）

单页 HTML 仪表盘，包含：
- 顶部：参数说明 + 总览统计
- 中部：对比表（可排序）
- 下部：权益曲线对比图（嵌入 PNG）
- 单标的详情折叠区：带买卖点标记的 K 线 + 均线图、回撤曲线、交易明细表

---

## 6. 验收标准

1. **正确性**：无未来函数，信号日次日开盘价成交；累计回报与逐笔交易可对账一致。
2. **健壮性**：空数据、单边上涨/下跌、长期无信号等场景不报错，返回合理默认值。
3. **指标校验**：MDD ∈ [0,1]、夏普为实数、累计回报与权益终值/初值一致。
4. **可复现**：固定随机种子（如有）、参数全部可配置、数据缓存到本地 CSV。
5. **可视化**：中文正常显示，涨红跌绿，图例清晰，对比图归一化。
6. **可扩展**：新增标的只需改配置列表，无需改核心代码。

---

## 7. 风险与局限（课程说明）

- **过拟合风险**：固定 (5,20) 参数为经典默认，未做参数寻优，结果反映该参数集的样本内表现，不构成投资建议。
- **简化假设**：未考虑涨跌停、停牌、分红送转、冲击成本随成交量变化等真实摩擦。
- **样本局限**：回测区间有限，策略在牛市/熊市/震荡市的表现差异需结合市场周期解读。
