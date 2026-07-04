#!/usr/bin/env python3
"""
股价技术指标计算与可视化
支持任意股价CSV数据，自动计算 RSI / MACD / 布林带 并绘图

CSV要求: 至少包含 date, close 列 (open, high, low, volume, amount 可选)
用法:   python technical_indicators.py data.csv
       python technical_indicators.py data.csv --output result.png
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
import pandas as pd

# —— 自动检测中文字体 (优先 Microsoft YaHei) ——
_CN_FONT = None
_CN_NAME = None
for _fn in fm.findSystemFonts():
    try:
        f = fm.FontProperties(fname=_fn)
        name = f.get_name()
        if "Microsoft YaHei" in name:
            _CN_FONT = f
            _CN_NAME = name
            break
    except Exception:
        pass
if _CN_FONT is None:
    for _fn in fm.findSystemFonts():
        try:
            f = fm.FontProperties(fname=_fn)
            name = f.get_name()
            if any(kw in name for kw in ["SimHei", "SimSun", "FangSong", "KaiTi", "Microsoft JhengHei", "Noto Sans CJK"]):
                _CN_FONT = f
                _CN_NAME = name
                break
        except Exception:
            pass
if _CN_FONT is None:
    _CN_FONT = fm.FontProperties()
    _CN_NAME = "sans-serif"
matplotlib.rcParams["font.family"] = _CN_NAME
matplotlib.rcParams["axes.unicode_minus"] = False
print(f"[Font] 使用字体: {_CN_NAME}")


class TechnicalIndicators:
    """计算 RSI, MACD, 布林带"""

    @staticmethod
    def rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """RSI — 相对强弱指标, Wilder平滑法"""
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi[avg_loss == 0] = 100.0
        return rsi.round(2)

    @staticmethod
    def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """MACD — 指数平滑异同移动平均线"""
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        histogram = (dif - dea) * 2
        return dif.round(4), dea.round(4), histogram.round(4)

    @staticmethod
    def bollinger(close: pd.Series, period: int = 20, num_std: float = 2.0):
        """布林带 — 中轨=MA, 上下轨=MA±N*σ"""
        mid = close.rolling(window=period, min_periods=period).mean()
        std = close.rolling(window=period, min_periods=period).std(ddof=0)
        upper = mid + num_std * std
        lower = mid - num_std * std
        return upper.round(4), mid.round(4), lower.round(4)


def load_csv(path: str) -> pd.DataFrame:
    """加载股价CSV, 自动解析日期列"""
    df = pd.read_csv(path, parse_dates=["date"] if "date" in pd.read_csv(path, nrows=0).columns else False)

    if "date" not in df.columns:
        raise ValueError("CSV必须包含 'date' 列")

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    required = {"close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要列: {missing}")

    # 清理: 确保数值列无空值
    for col in ["open", "high", "low", "close", "volume", "amount"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def build_signal_events(df: pd.DataFrame):
    """
    识别金叉/死叉、RSI超买超卖交叉事件
    返回 list[(event_type, date, value)]
    """
    events = []

    # MACD 金叉/死叉 (跳过前 35 个数据点 warmup)
    if "dif" in df.columns and "dea" in df.columns:
        warmup = 35
        dif = df["dif"].values
        dea = df["dea"].values
        for i in range(warmup, len(dif)):
            if pd.notna(dif[i]) and pd.notna(dea[i]):
                if dif[i] > dea[i] and dif[i - 1] <= dea[i - 1]:
                    events.append(("golden_cross", df["date"].iloc[i], dif[i]))
                elif dif[i] < dea[i] and dif[i - 1] >= dea[i - 1]:
                    events.append(("death_cross", df["date"].iloc[i], dif[i]))

    # RSI 超买超卖穿越 (跳过前 20 个数据点 warmup)
    if "rsi" in df.columns:
        rsi = df["rsi"].values
        warmup = 20
        for i in range(warmup, len(rsi)):
            if pd.notna(rsi[i]) and pd.notna(rsi[i - 1]):
                if rsi[i - 1] <= 30 and rsi[i] > 30:
                    events.append(("rsi_oversold_out", df["date"].iloc[i], rsi[i]))
                elif rsi[i - 1] > 30 and rsi[i] <= 30:
                    events.append(("rsi_oversold_in", df["date"].iloc[i], rsi[i]))
                elif rsi[i - 1] < 70 and rsi[i] >= 70:
                    events.append(("rsi_overbought_in", df["date"].iloc[i], rsi[i]))
                elif rsi[i - 1] >= 70 and rsi[i] < 70:
                    events.append(("rsi_overbought_out", df["date"].iloc[i], rsi[i]))

    return events


def plot_all(df: pd.DataFrame, events: list, output_path: str, title_prefix: str = ""):
    """绘制4面板图: K线+布林带 / 成交量 / MACD / RSI"""
    df = df.copy()

    RED   = "#e74c3c"
    GREEN = "#27ae60"

    n = len(df)
    # 使用整数索引作为X轴，消除非交易日空隙
    idx = np.arange(n)
    bar_width = 0.7

    # 选取适中间隔的日期作为刻度标签 (约12个)
    tick_step = max(1, n // 12)
    tick_positions = idx[::tick_step]
    tick_labels = [d.strftime("%Y-%m") for d in df["date"].iloc[::tick_step]]

    has_ohlc = all(c in df.columns for c in ["open", "high", "low"])

    fig, axes = plt.subplots(4, 1, figsize=(22, 15), sharex=True,
                              gridspec_kw={"height_ratios": [2.8, 0.8, 1.2, 1.2]})
    fig.suptitle(f"{title_prefix} 技术指标综合分析", fontsize=18, fontweight="bold", y=0.99)

    # ===== Panel 1: K线 + 布林带 =====
    ax1 = axes[0]

    if has_ohlc:
        opens  = df["open"].values
        highs  = df["high"].values
        lows   = df["low"].values
        closes = df["close"].values
    else:
        opens = closes = df["close"].values
        highs = lows  = df["close"].values

    ax1.vlines(idx, lows, highs, colors=[RED if c >= o else GREEN for c, o in zip(closes, opens)],
               linewidths=0.7, alpha=0.85)

    up   = closes >= opens
    down = ~up

    if up.any():
        ax1.bar(idx[up],   closes[up] - opens[up],  bar_width, bottom=opens[up],
                color=RED, edgecolor=RED, linewidth=0.5, alpha=0.95)
    if down.any():
        ax1.bar(idx[down], opens[down] - closes[down], bar_width, bottom=closes[down],
                color=GREEN, edgecolor=GREEN, linewidth=0.5, alpha=0.95)

    if all(c in df.columns for c in ["bb_upper", "bb_mid", "bb_lower"]):
        mask = df["bb_mid"].notna()
        ax1.plot(idx[mask], df["bb_upper"].values[mask], "--", color="gray", alpha=0.6, linewidth=0.8, label="布林上轨")
        ax1.plot(idx[mask], df["bb_mid"].values[mask],   "-",  color="#2196f3", alpha=0.7, linewidth=1.2, label="布林中轨(MA20)")
        ax1.plot(idx[mask], df["bb_lower"].values[mask], "--", color="gray", alpha=0.6, linewidth=0.8, label="布林下轨")
        ax1.fill_between(idx[mask], df["bb_lower"].values[mask], df["bb_upper"].values[mask],
                          alpha=0.05, color="blue")

    ax1.set_ylabel("价格 (元)", fontsize=11)
    ax1.legend(loc="upper left", fontsize=9, framealpha=0.8)
    ax1.grid(True, alpha=0.25)
    ax1.set_title("K线 + 布林带 (Bollinger Bands 20,2)", fontsize=13, loc="left")

    # ===== Panel 2: Volume =====
    ax2 = axes[1]
    if "volume" in df.columns and df["volume"].sum() > 0:
        colors_vol = [RED if df["close"].iloc[i] >= opens[i] else GREEN for i in range(n)]
        ax2.bar(idx, df["volume"].values, width=bar_width, color=colors_vol, alpha=0.55)
        ax2.set_ylabel("成交量 (手)", fontsize=11)
    ax2.set_title("成交量", fontsize=13, loc="left")
    ax2.grid(True, alpha=0.25)

    # ===== Panel 3: MACD =====
    ax3 = axes[2]
    if all(c in df.columns for c in ["dif", "dea", "macd_hist"]):
        hist = df["macd_hist"].values
        colors_hist = [RED if v >= 0 else GREEN for v in hist]
        ax3.bar(idx, hist, width=bar_width, color=colors_hist, alpha=0.5, label="柱线")
        ax3.plot(idx, df["dif"].values, "-", color="#1a73e8", linewidth=1.2, label="DIF")
        ax3.plot(idx, df["dea"].values, "-", color="#e37400", linewidth=1.2, label="DEA")
        ax3.axhline(y=0, color="black", linewidth=0.5)

        date_to_idx = {d: i for i, d in enumerate(df["date"])}
        for evt_type, evt_date, evt_val in events:
            if evt_date in date_to_idx:
                pos = date_to_idx[evt_date]
                if evt_type == "golden_cross":
                    ax3.scatter(pos, evt_val, marker="^", color=RED, s=60, zorder=5, edgecolors="white", linewidths=0.5)
                elif evt_type == "death_cross":
                    ax3.scatter(pos, evt_val, marker="v", color=GREEN, s=60, zorder=5, edgecolors="white", linewidths=0.5)

        ax3.legend(loc="upper left", fontsize=9, framealpha=0.8)
    ax3.set_ylabel("MACD", fontsize=11)
    ax3.set_title("MACD (12, 26, 9)", fontsize=13, loc="left")
    ax3.grid(True, alpha=0.25)

    # ===== Panel 4: RSI =====
    ax4 = axes[3]
    if "rsi" in df.columns:
        rsi_vals = df["rsi"].values
        valid = pd.notna(rsi_vals)
        ax4.plot(idx[valid], rsi_vals[valid], "-", color="#7b1fa2", linewidth=1.2, label="RSI(14)")
        ax4.axhline(y=70, color=RED, linewidth=0.8, linestyle="--", alpha=0.6, label="超买 70")
        ax4.axhline(y=30, color=GREEN, linewidth=0.8, linestyle="--", alpha=0.6, label="超卖 30")
        ax4.axhline(y=50, color="gray", linewidth=0.5, linestyle=":", alpha=0.4)
        ax4.fill_between(idx[valid], 30, 70, alpha=0.03, color="gray")
        ax4.set_ylim(-2, 102)

        date_to_idx = {d: i for i, d in enumerate(df["date"])}
        for evt_type, evt_date, evt_val in events:
            if "rsi" in evt_type and evt_date in date_to_idx:
                pos = date_to_idx[evt_date]
                clr = RED if "overbought" in evt_type else GREEN
                marker = "v" if "in" in evt_type else "^"
                ax4.scatter(pos, evt_val, marker=marker, color=clr,
                            s=50, zorder=5, edgecolors="white", linewidths=0.5)

        ax4.legend(loc="upper left", fontsize=9, framealpha=0.8)
    ax4.set_ylabel("RSI", fontsize=11)
    ax4.set_xlabel("日期", fontsize=12)
    ax4.set_title("RSI (14)", fontsize=13, loc="left")
    ax4.grid(True, alpha=0.25)

    # X 轴: 整数索引 + 日期标签
    for ax in axes:
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=30, ha="right", fontsize=9)
        ax.set_xlim(idx[0] - 1, idx[-1] + 1)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] 图表已保存至: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="股价技术指标计算与可视化")
    parser.add_argument("csv", help="股价CSV文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出图片路径 (默认: 同目录 technical_chart.png)")
    parser.add_argument("--title", default=None, help="图表标题前缀 (如: 埃斯顿 002747)")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"[ERROR] 文件不存在: {csv_path}")
        sys.exit(1)

    if args.output is None:
        output_path = str(csv_path.parent / "technical_chart.png")
    else:
        output_path = args.output

    # —— 1. 加载 ——
    print(f"[1/4] 加载数据: {csv_path}")
    df = load_csv(str(csv_path))
    print(f"      共 {len(df)} 条记录, {df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['date'].iloc[-1].strftime('%Y-%m-%d')}")

    # —— 2. 计算指标 ——
    print("[2/4] 计算技术指标...")
    ti = TechnicalIndicators()
    df["rsi"] = ti.rsi(df["close"])
    df["dif"], df["dea"], df["macd_hist"] = ti.macd(df["close"])
    df["bb_upper"], df["bb_mid"], df["bb_lower"] = ti.bollinger(df["close"])
    print(f"      RSI(14)     : {df['rsi'].iloc[-1]:.2f}")
    print(f"      MACD DIF/DEA: {df['dif'].iloc[-1]:.4f} / {df['dea'].iloc[-1]:.4f}")
    print(f"      布林上/中/下 : {df['bb_upper'].iloc[-1]:.2f} / {df['bb_mid'].iloc[-1]:.2f} / {df['bb_lower'].iloc[-1]:.2f}")

    # —— 3. 识别信号事件 ——
    print("[3/4] 识别买卖信号...")
    events = build_signal_events(df)
    golden = sum(1 for e in events if e[0] == "golden_cross")
    death = sum(1 for e in events if e[0] == "death_cross")
    print(f"      金叉: {golden} 次  死叉: {death} 次")

    # —— 4. 绘图 ——
    print("[4/4] 生成图表...")
    title = args.title or csv_path.stem
    plot_all(df, events, output_path, title)
    print("===== 完成 =====")


if __name__ == "__main__":
    main()
