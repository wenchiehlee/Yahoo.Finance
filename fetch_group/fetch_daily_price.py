#!/usr/bin/env python3
"""Fetch ~2 年逐日收盤價（TW 觀察名單 + ConceptStocks 美股 Ticker），輸出長格式 CSV。

給 GoogleSheet.Banks/fugle_stock_advisor.py 的買進時機評分用（RSI/MA60/MA200/52週高低），
取代原本每次執行都即時打 yfinance 的做法，改成每日排程先抓好存成 CSV 再同步過去。

增量抓取：已有資料的代號只抓「既有最後一筆日期 - 緩衝天數」到今天（緩衝天數是為了蓋掉
yfinance auto_adjust 對近期資料的回溯修正，不是單純漏抓一天就永遠補不回來），跟舊資料合併
（同一天以新抓的為準）後只保留最近 RETENTION_DAYS 天，避免 CSV 隨時間無限增大，也避免每天
重抓整段 2 年、既慢又浪費 API 額度。全新代號（舊資料裡完全沒有）才整段抓 2 年當作 bootstrap。

台股不預先假設上市（.TW）或上櫃（.TWO），兩個 suffix 都試，抓得到資料的那個就是對的
（避免另外維護一份跟 GoogleSheet.Banks 裡 TWO_CODES 重複、容易兜不齊的清單）。
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parents[1]

RAW_COLUMNS = [
    "stock_code", "company_name", "market", "yahoo_symbol",
    "交易_日期", "開盤價", "最高價", "最低價", "收盤價", "volume",
    "download_timestamp",
]

INCREMENTAL_OVERLAP_DAYS = 5  # 從「既有最後一筆日期 - 這麼多天」開始重抓，蓋掉近期可能被回溯修正的資料
RETENTION_DAYS = 760          # 只保留最近這麼多天，留一點餘裕給 252 個交易日的滾動視窗


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


def load_existing_by_code(path: Path):
    """回傳 {stock_code: [row dict, ...]}。代號不在裡面（新代號／檔案第一次產生）時，
    呼叫端會退回整段 2 年 bootstrap 抓取。"""
    by_code = {}
    for row in read_csv_rows(path):
        by_code.setdefault(row.get("stock_code", ""), []).append(row)
    return by_code


def fetch_history(yahoo_symbol: str, start: str | None = None):
    try:
        if start:
            hist = yf.download(yahoo_symbol, start=start, progress=False, auto_adjust=True)
        else:
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


def merge_rows(existing_rows, new_rows, retention_days):
    """existing + new 合併，同一天（交易_日期）以 new 為準，依日期排序，
    只保留 retention_days 天內的資料。"""
    by_date = {r["交易_日期"]: r for r in existing_rows}
    for r in new_rows:
        by_date[r["交易_日期"]] = r
    cutoff = (datetime.now(timezone.utc) - timedelta(days=retention_days)).strftime("%Y-%m-%d")
    merged = [r for r in by_date.values() if r["交易_日期"] >= cutoff]
    merged.sort(key=lambda r: r["交易_日期"])
    return merged


def fetch_one(code, name, market, resolve_symbols, existing_by_code, sleep_sec):
    """resolve_symbols: 依序嘗試的 yahoo_symbol 清單（TW 是 [code.TW, code.TWO]，US 是 [code]）。
    回傳 (merged_rows, resolved_symbol) 或 (None, None) 代表整段都抓失敗。"""
    existing = existing_by_code.get(code, [])
    last_date = max((r["交易_日期"] for r in existing), default=None)

    for symbol in resolve_symbols:
        if last_date:
            start = (datetime.strptime(last_date, "%Y-%m-%d") - timedelta(days=INCREMENTAL_OVERLAP_DAYS)).strftime("%Y-%m-%d")
            hist = fetch_history(symbol, start=start)
        else:
            hist = fetch_history(symbol)  # 全新代號，整段 2 年 bootstrap
        if hist is not None:
            new_rows = rows_from_history(code, name, market, symbol, hist)
            merged = merge_rows(existing, new_rows, RETENTION_DAYS) if existing else new_rows
            return merged, symbol
        time.sleep(sleep_sec)
    return None, None


def fetch_tw(targets, existing_by_code, sleep_sec):
    all_rows, failed = [], []
    for t in targets:
        code = t["stock_code"]
        symbols = [f"{code}.TW", f"{code}.TWO"]
        merged, resolved = fetch_one(code, t["company_name"], "TW", symbols, existing_by_code, sleep_sec)
        if merged is not None:
            all_rows.extend(merged)
        else:
            failed.append(code)
            # 這次沒抓到，保留舊資料（若有）避免整檔股票的歷史憑空消失
            all_rows.extend(existing_by_code.get(code, []))
        print(f"  TW {code} {t['company_name']}: {'OK ' + resolved if resolved else 'FAILED'}")
        time.sleep(sleep_sec)
    return all_rows, failed


def fetch_us(targets, existing_by_code, sleep_sec):
    all_rows, failed = [], []
    for t in targets:
        ticker = t["stock_code"]
        merged, resolved = fetch_one(ticker, t["company_name"], "US", [ticker], existing_by_code, sleep_sec)
        if merged is not None:
            all_rows.extend(merged)
            print(f"  US {ticker}: OK")
        else:
            failed.append(ticker)
            all_rows.extend(existing_by_code.get(ticker, []))
            print(f"  US {ticker}: FAILED")
        time.sleep(sleep_sec)
    return all_rows, failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tw-list", default=str(REPO_ROOT / "StockID_TWSE_TPEX.csv"))
    parser.add_argument("--us-list", default=str(REPO_ROOT / "data" / "ConceptStocks" / "raw_conceptstock_company_metadata.csv"))
    parser.add_argument("--output-csv", default=str(REPO_ROOT / "data" / "reports" / "raw_yahoo_finance_daily_price.csv"))
    parser.add_argument("--sleep-sec", type=float, default=0.3)
    parser.add_argument("--full-refresh", action="store_true",
                         help="忽略既有 CSV，全部代號整段重抓 2 年（正常增量抓取失效或要重建基準線時用）")
    args = parser.parse_args()

    out_path = Path(args.output_csv)
    tw_targets = load_tw_targets(Path(args.tw_list))
    us_targets = load_us_targets(Path(args.us_list))
    existing_by_code = {} if args.full_refresh else load_existing_by_code(out_path)
    print(f"TW targets: {len(tw_targets)}, US targets: {len(us_targets)}, "
          f"既有代號數: {len(existing_by_code)}{'（忽略，全量重抓）' if args.full_refresh else ''}")

    print("== 抓取台股 ==")
    tw_rows, tw_failed = fetch_tw(tw_targets, existing_by_code, args.sleep_sec)
    print("== 抓取美股 ==")
    us_rows, us_failed = fetch_us(us_targets, existing_by_code, args.sleep_sec)

    all_rows = tw_rows + us_rows
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RAW_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n寫入 {out_path}：{len(all_rows)} 筆（TW {len(tw_rows)}, US {len(us_rows)}）")
    if tw_failed:
        print(f"TW 這次抓取失敗（沿用舊資料）: {', '.join(tw_failed)}")
    if us_failed:
        print(f"US 這次抓取失敗（沿用舊資料）: {', '.join(us_failed)}")


if __name__ == "__main__":
    main()
