#!/usr/bin/env python3
"""Fetch ~2 年逐日收盤價（TW 觀察名單 + ConceptStocks 美股 Ticker），輸出長格式 CSV。

給 GoogleSheet.Banks/fugle_stock_advisor.py 的買進時機評分用（RSI/MA60/MA200/52週高低），
取代原本每次執行都即時打 yfinance 的做法，改成每日排程先抓好存成 CSV 再同步過去。

台股不預先假設上市（.TW）或上櫃（.TWO），兩個 suffix 都試，抓得到資料的那個就是對的
（避免另外維護一份跟 GoogleSheet.Banks 裡 TWO_CODES 重複、容易兜不齊的清單）。
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parents[1]

RAW_COLUMNS = [
    "stock_code", "company_name", "market", "yahoo_symbol",
    "交易_日期", "開盤價", "最高價", "最低價", "收盤價", "volume",
    "download_timestamp",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def read_csv_rows(path: Path):
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_tw_targets(path: Path):
    targets = []
    for row in read_csv_rows(path):
        code = (row.get("代號") or "").strip()
        name = (row.get("名稱") or "").strip()
        if code:
            targets.append({"stock_code": code, "company_name": name})
    return targets


def load_us_targets(path: Path):
    targets, seen = [], set()
    for row in read_csv_rows(path):
        ticker = (row.get("Ticker") or "").strip()
        name = (row.get("公司名稱") or "").strip()
        if ticker and ticker != "-" and ticker not in seen:
            seen.add(ticker)
            targets.append({"stock_code": ticker, "company_name": name})
    return targets


def fetch_history(yahoo_symbol: str):
    try:
        hist = yf.download(yahoo_symbol, period="2y", progress=False, auto_adjust=True)
    except Exception:
        return None
    if hist is None or hist.empty:
        return None
    return hist


def rows_from_history(stock_code, company_name, market, yahoo_symbol, hist):
    ts = utc_now()
    out = []
    for idx, row in hist.iterrows():
        def _f(col):
            v = row.get(col)
            try:
                return float(v.iloc[0]) if hasattr(v, "iloc") else float(v)
            except (TypeError, ValueError):
                return ""
        out.append({
            "stock_code": stock_code, "company_name": company_name, "market": market,
            "yahoo_symbol": yahoo_symbol, "交易_日期": idx.strftime("%Y-%m-%d"),
            "開盤價": _f("Open"), "最高價": _f("High"), "最低價": _f("Low"), "收盤價": _f("Close"),
            "volume": _f("Volume"), "download_timestamp": ts,
        })
    return out


def fetch_tw(targets, sleep_sec):
    all_rows, failed = [], []
    for t in targets:
        code = t["stock_code"]
        resolved = None
        for suffix in ("TW", "TWO"):
            symbol = f"{code}.{suffix}"
            hist = fetch_history(symbol)
            if hist is not None:
                resolved = symbol
                all_rows.extend(rows_from_history(code, t["company_name"], "TW", symbol, hist))
                break
            time.sleep(sleep_sec)
        if resolved is None:
            failed.append(code)
        print(f"  TW {code} {t['company_name']}: {'OK ' + resolved if resolved else 'FAILED'}")
        time.sleep(sleep_sec)
    return all_rows, failed


def fetch_us(targets, sleep_sec):
    all_rows, failed = [], []
    for t in targets:
        ticker = t["stock_code"]
        hist = fetch_history(ticker)
        if hist is not None:
            all_rows.extend(rows_from_history(ticker, t["company_name"], "US", ticker, hist))
            print(f"  US {ticker}: OK")
        else:
            failed.append(ticker)
            print(f"  US {ticker}: FAILED")
        time.sleep(sleep_sec)
    return all_rows, failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tw-list", default=str(REPO_ROOT / "StockID_TWSE_TPEX.csv"))
    parser.add_argument("--us-list", default=str(REPO_ROOT / "data" / "ConceptStocks" / "raw_conceptstock_company_metadata.csv"))
    parser.add_argument("--output-csv", default=str(REPO_ROOT / "data" / "reports" / "raw_yahoo_finance_daily_price.csv"))
    parser.add_argument("--sleep-sec", type=float, default=0.3)
    args = parser.parse_args()

    tw_targets = load_tw_targets(Path(args.tw_list))
    us_targets = load_us_targets(Path(args.us_list))
    print(f"TW targets: {len(tw_targets)}, US targets: {len(us_targets)}")

    print("== 抓取台股 ==")
    tw_rows, tw_failed = fetch_tw(tw_targets, args.sleep_sec)
    print("== 抓取美股 ==")
    us_rows, us_failed = fetch_us(us_targets, args.sleep_sec)

    all_rows = tw_rows + us_rows
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n寫入 {out_path}：{len(all_rows)} 筆（TW {len(tw_rows)}, US {len(us_rows)}）")
    if tw_failed:
        print(f"TW 抓取失敗（找不到 .TW/.TWO）: {', '.join(tw_failed)}")
    if us_failed:
        print(f"US 抓取失敗: {', '.join(us_failed)}")


if __name__ == "__main__":
    main()
