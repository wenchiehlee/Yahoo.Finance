#!/usr/bin/env python3
"""把當日 raw_yahoo_finance_summary_latest.csv 的關鍵共識欄位追加到
data/reports/raw_yahoo_finance_consensus_daily.csv（逐日累積、永不改寫舊列）。

目的：前瞻 EPS 訊號（前瞻PE門檻/EPS成長/上修動能/盈餘驚喜）目前是
GoogleSheet.Banks 買進候選 KPI 裡唯一沒有回測背書的一塊——因為分析師預估沒有歷史
時間序列（Wayback 管線解析成功率過低、summary 檔每天被覆寫）。這支腳本讓歷史從
「git 考古」變成正式資料：累積 6~12 個月後，就能像技術面子項一樣對前瞻 EPS 家族做
回歸驗證（訊號日的前瞻PE/預估動能 vs 之後 60/120 日報酬）。

去重鍵 (stock_code, forecast_asof_date)。--backfill-git 模式會走訪 git 歷史裡
summary 檔的所有版本，把過去的快照一次補進來（每天的排程 commit 就是天然的逐日存檔）。
"""
from __future__ import annotations

import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_CSV = REPO_ROOT / "data" / "reports" / "raw_yahoo_finance_summary_latest.csv"
OUT_CSV = REPO_ROOT / "data" / "reports" / "raw_yahoo_finance_consensus_daily.csv"

KEEP_COLUMNS = [
    "stock_code", "company_name", "market", "forecast_asof_date",
    "earnings_0q_avg", "earnings_1q_avg", "earnings_0y_avg", "earnings_1y_avg",
    "revenue_0y_avg", "revenue_1y_avg",
    "eps_trend_0y_current", "eps_trend_1y_current",
    "eps_beat_count_4q", "eps_surprise_avg_4q_pct",
    "cross_check_status", "process_timestamp",
]
KEY = ("stock_code", "forecast_asof_date")


def rows_from_text(text):
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        if not (row.get("stock_code") and row.get("forecast_asof_date")):
            continue
        out.append({c: row.get(c, "") for c in KEEP_COLUMNS})
    return out


def load_existing():
    keys, rows = set(), []
    if OUT_CSV.exists():
        with open(OUT_CSV, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                rows.append(row)
                keys.add(tuple(row.get(k, "") for k in KEY))
    return keys, rows


def append_rows(new_rows, keys, rows):
    added = 0
    for r in new_rows:
        k = tuple(str(r.get(c, "")) for c in KEY)
        if k in keys:
            continue
        rows.append(r)
        keys.add(k)
        added += 1
    return added


def write_out(rows):
    rows.sort(key=lambda r: (r.get("forecast_asof_date", ""), r.get("stock_code", "")))
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=KEEP_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill-git", action="store_true",
                        help="走訪 git 歷史裡 summary 檔的所有版本一次回填（首次建檔用）")
    args = parser.parse_args()

    keys, rows = load_existing()
    total_added = 0

    if args.backfill_git:
        rel = SUMMARY_CSV.relative_to(REPO_ROOT).as_posix()
        hashes = subprocess.run(
            ["git", "log", "--format=%H", "--", rel],
            cwd=REPO_ROOT, capture_output=True, text=True).stdout.split()
        print(f"git 歷史版本數: {len(hashes)}")
        for h in hashes:
            r = subprocess.run(["git", "show", f"{h}:{rel}"], cwd=REPO_ROOT,
                               capture_output=True)
            if r.returncode != 0:
                continue
            text = r.stdout.decode("utf-8-sig", errors="ignore")
            total_added += append_rows(rows_from_text(text), keys, rows)

    if SUMMARY_CSV.exists():
        with open(SUMMARY_CSV, encoding="utf-8-sig") as f:
            total_added += append_rows(rows_from_text(f.read()), keys, rows)

    write_out(rows)
    dates = {r["forecast_asof_date"] for r in rows}
    print(f"寫入 {OUT_CSV.name}：總 {len(rows)} 列、{len(dates)} 個快照日（本次新增 {total_added}）")


if __name__ == "__main__":
    main()
