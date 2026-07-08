#!/usr/bin/env python3
"""
处理 Tushare 拉取的日线 + 复权因子，生成前复权(qfq)数据。
输出:
  - task3/backtest_data/<code>.csv   每只标的的 CSV (date,open,high,low,close,volume,amount)
  - task3/backtest_data/data_all.json  供 HTML 内嵌的统一 JSON
"""
import json
import os
from collections import defaultdict

WORKDIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(WORKDIR)  # 量化课程
# 数据文件在 .workbuddy 缓存里
RESULT_DIR = os.path.join(os.path.expanduser("~"), ".workbuddy", "projects",
                          "c-Users-chen-Desktop-量化课程",
                          "61f4a438-51ec-4f01-aa84-1a830f74d259", "tool-results")
DAILY_FILE = os.path.join(RESULT_DIR, "mcp-connector-proxy-tushareMcp_daily-1783522540168-e6f2dd.txt")
ADJ_FILE = os.path.join(RESULT_DIR, "mcp-connector-proxy-tushareMcp_adj_factor-1783522562432-652e95.txt")

OUT_DIR = os.path.join(BASE, "task3", "backtest_data")
os.makedirs(OUT_DIR, exist_ok=True)

NAME_MAP = {
    "002747.SZ": "埃斯顿",
    "600519.SH": "贵州茅台",
    "300750.SZ": "宁德时代",
    "600036.SH": "招商银行",
    "002594.SZ": "比亚迪",
}

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

daily = load_json(DAILY_FILE)
adj = load_json(ADJ_FILE)

# 按 ts_code 分组
daily_by_code = defaultdict(list)
for r in daily:
    daily_by_code[r["ts_code"]].append(r)

adj_by_code = defaultdict(dict)  # code -> {trade_date: adj_factor}
for r in adj:
    adj_by_code[r["ts_code"]][r["trade_date"]] = r["adj_factor"]

all_data = {}
for code, rows in daily_by_code.items():
    # 找该股票最新(最大)的 adj_factor 作为前复权基准
    af_map = adj_by_code.get(code, {})
    if not af_map:
        print(f"[WARN] {code} 无复权因子, 跳过")
        continue
    latest_af = max(af_map.values())  # 最新日期对应的因子最大
    # 排序: 按 trade_date 升序
    rows.sort(key=lambda x: x["trade_date"])
    out_rows = []
    for r in rows:
        td = r["trade_date"]
        af = af_map.get(td, latest_af)
        scale = af / latest_af  # 前复权比例
        date_iso = f"{td[:4]}-{td[4:6]}-{td[6:8]}"
        out_rows.append({
            "date": date_iso,
            "open": round(r["open"] * scale, 4),
            "high": round(r["high"] * scale, 4),
            "low": round(r["low"] * scale, 4),
            "close": round(r["close"] * scale, 4),
            "volume": round(r["vol"], 2),       # 手
            "amount": round(r["amount"] * 1000, 2),  # 千元 -> 元
        })
    all_data[code] = {
        "name": NAME_MAP.get(code, code),
        "code": code,
        "data": out_rows,
    }
    # 写 CSV
    csv_path = os.path.join(OUT_DIR, f"{code.split('.')[0]}.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("date,open,high,low,close,volume,amount\n")
        for o in out_rows:
            f.write(f"{o['date']},{o['open']},{o['high']},{o['low']},{o['close']},{o['volume']},{o['amount']}\n")
    print(f"[OK] {code} {NAME_MAP.get(code)}: {len(out_rows)} 条, "
          f"{out_rows[0]['date']} ~ {out_rows[-1]['date']} -> {csv_path}")

# 统一 JSON
json_path = os.path.join(OUT_DIR, "data_all.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(all_data, f, ensure_ascii=False)
print(f"[OK] 统一数据 -> {json_path}")
print("===== 完成 =====")
