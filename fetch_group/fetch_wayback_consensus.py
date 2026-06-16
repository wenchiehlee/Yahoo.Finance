#!/usr/bin/env python3
"""Fetch historical Yahoo Finance analyst analysis from Wayback Machine and compile it."""

import os
import sys
import re
import time
import csv
import datetime
import urllib.parse
import urllib.request
import json
import numpy as np
import pandas as pd
from pathlib import Path

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = os.path.join(REPO_ROOT, "configs", "default.yaml")
STOCK_LIST_PATH = os.path.join(REPO_ROOT, "StockID_TWSE_TPEX_focus.csv")
OUTPUT_CSV = os.path.join(REPO_ROOT, "data", "reports", "wayback_yahoo_finance_consensus.csv")

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    import yaml
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_focus_stocks():
    targets = []
    if os.path.exists(STOCK_LIST_PATH):
        with open(STOCK_LIST_PATH, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                code = (row.get("代號") or "").strip()
                name = (row.get("名稱") or "").strip()
                if code:
                    targets.append({"code": code, "name": name})
    if not targets:
        targets = [
            {"code": "2330", "name": "台積電"},
            {"code": "2357", "name": "華碩"},
            {"code": "2382", "name": "廣達"},
            {"code": "2480", "name": "敦陽科"}
        ]
    return targets

def parse_val_with_suffix(val_str):
    if pd.isna(val_str) or not val_str or str(val_str).strip() == "N/A" or str(val_str).strip() == "-":
        return np.nan
    val_str = str(val_str).strip().replace(",", "")
    
    # Check for unit suffixes
    multiplier = 1.0
    if val_str.endswith("B"):
        multiplier = 1e9
        val_str = val_str[:-1]
    elif val_str.endswith("M"):
        multiplier = 1e6
        val_str = val_str[:-1]
    elif val_str.endswith("T"):
        multiplier = 1e12
        val_str = val_str[:-1]
    elif val_str.endswith("k") or val_str.endswith("K"):
        multiplier = 1e3
        val_str = val_str[:-1]
        
    try:
        return float(val_str) * multiplier
    except ValueError:
        return np.nan

def fetch_wayback_snapshots(url, limit_months=24):
    """Query Wayback CDX API for historical snapshot timestamps of the URL."""
    encoded_url = urllib.parse.quote_plus(url)
    cdx_url = f"https://web.archive.org/cdx/search/cdx?url={encoded_url}&output=json&statuscode=200"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(cdx_url, headers=headers)
    
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
                if len(data) <= 1:
                    return []
                
                header = data[0]
                rows = data[1:]
                
                ts_idx = header.index("timestamp")
                orig_idx = header.index("original")
                
                snapshots = []
                for r in rows:
                    snapshots.append({
                        "timestamp": r[ts_idx],
                        "original": r[orig_idx]
                    })
                
                monthly_snapshots = {}
                for snap in snapshots:
                    ts = snap["timestamp"]
                    year_month = ts[:6]
                    if year_month not in monthly_snapshots or ts > monthly_snapshots[year_month]["timestamp"]:
                        monthly_snapshots[year_month] = snap
                
                sorted_snaps = sorted(list(monthly_snapshots.values()), key=lambda x: x["timestamp"])
                return sorted_snaps[-limit_months:]
                
        except Exception as e:
            print(f"Attempt {attempt+1} failed to call Wayback CDX API: {e}")
            if attempt < 2:
                time.sleep(3.0)
                
    return []

def download_html(timestamp, original_url):
    """Download archived HTML page from Wayback Machine."""
    wayback_url = f"https://web.archive.org/web/{timestamp}/{original_url}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    req = urllib.request.Request(wayback_url, headers=headers)
    
    # Retry logic
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                return response.read().decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"Attempt {attempt+1} failed to download snapshot {timestamp}: {e}")
            time.sleep(3.0)
    return None

def parse_consensus_from_html(html_text):
    """Parse Revenue and Earnings estimate tables from HTML content."""
    try:
        dfs = pd.read_html(html_text)
    except Exception as e:
        return None
        
    revenue_df = None
    earnings_df = None
    
    for df in dfs:
        if df.empty or df.shape[1] < 2:
            continue
            
        # Standardize columns and rows
        first_col = str(df.columns[0]).strip()
        first_row_vals = [str(x).lower() for x in df.iloc[:, 0].tolist()]
        
        # Check if this is Earnings Estimate
        # Typical rows: 'Avg. Estimate', 'Low Estimate', etc.
        # Typical columns might contain "Current Qtr.", "Next Qtr.", "Current Year", "Next Year"
        has_avg = any("avg" in str(x).lower() or "平均" in str(x) for x in first_row_vals)
        
        # Determine if Earnings or Revenue
        # Revenue table will contain clues like 'sales growth' or 'year ago sales' or 'revenue' in headers/index
        is_revenue = False
        is_earnings = False
        
        # Flatten all text in DataFrame to find keywords
        all_text = " ".join([str(x) for x in df.values.flatten()] + [str(c) for c in df.columns])
        all_text_lower = all_text.lower()
        
        if has_avg:
            if "sales" in all_text_lower or "revenue" in all_text_lower or "營收" in all_text or "收益預估" in all_text:
                is_revenue = True
            elif "eps" in all_text_lower or "earnings" in all_text_lower or "每股" in all_text or "盈利預估" in all_text:
                is_earnings = True
                
        if is_revenue and revenue_df is None:
            revenue_df = df
        elif is_earnings and earnings_df is None:
            earnings_df = df
            
    if revenue_df is None and earnings_df is None:
        return None
        
    # Process tables into standard dict
    result = {
        "earnings_0q_avg": np.nan, "earnings_1q_avg": np.nan,
        "earnings_0y_avg": np.nan, "earnings_1y_avg": np.nan,
        "revenue_0q_avg": np.nan, "revenue_1q_avg": np.nan,
        "revenue_0y_avg": np.nan, "revenue_1y_avg": np.nan
    }
    
    def extract_avg_vals(df, is_rev):
        prefix = "revenue" if is_rev else "earnings"
        
        # Find the row containing average estimate
        avg_row_idx = None
        for idx, row in df.iterrows():
            row_label = str(row.iloc[0]).lower()
            if "avg" in row_label or "平均" in row_label:
                avg_row_idx = idx
                break
                
        if avg_row_idx is None:
            return
            
        avg_row = df.iloc[avg_row_idx]
        
        # Identify columns (0q, 1q, 0y, 1y)
        # Columns 1 to 4 should correspond to 0q, 1q, 0y, 1y respectively
        for col_idx in range(1, min(5, len(avg_row))):
            col_header = str(df.columns[col_idx]).lower()
            val = parse_val_with_suffix(avg_row.iloc[col_idx])
            
            # Map column index or header to period
            if "next qtr" in col_header or "+1q" in col_header:
                result[f"{prefix}_1q_avg"] = val
            elif "current qtr" in col_header or "0q" in col_header:
                result[f"{prefix}_0q_avg"] = val
            elif "next year" in col_header or "+1y" in col_header:
                result[f"{prefix}_1y_avg"] = val
            elif "current year" in col_header or "0y" in col_header:
                result[f"{prefix}_0y_avg"] = val
            else:
                # Fallback based on column index
                if col_idx == 1:
                    result[f"{prefix}_0q_avg"] = val
                elif col_idx == 2:
                    result[f"{prefix}_1q_avg"] = val
                elif col_idx == 3:
                    result[f"{prefix}_0y_avg"] = val
                elif col_idx == 4:
                    result[f"{prefix}_1y_avg"] = val

    if revenue_df is not None:
        extract_avg_vals(revenue_df, is_rev=True)
    if earnings_df is not None:
        extract_avg_vals(earnings_df, is_rev=False)
        
    return result

def main():
    config = load_config()
    targets = load_focus_stocks()
    targets = [t for t in targets if t["code"] in ["2330", "2357", "2382", "2480"]]
    
    # Determine default suffix
    suffix = ".TW"
    if config and "yahoo" in config:
        suffix = config["yahoo"].get("taiwan_default_suffix", ".TW")
        
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    
    all_records = []
    
    for t in targets:
        code = t["code"]
        name = t["name"]
        yahoo_symbol = f"{code}{suffix}"
        url = f"https://hk.finance.yahoo.com/quote/{yahoo_symbol}/analysis/"
        
        print(f"\n=======================================================")
        print(f"Target: {code} ({name}) - Yahoo Symbol: {yahoo_symbol}")
        print(f"Querying snapshots on Wayback Machine...")
        
        snapshots = fetch_wayback_snapshots(url, limit_months=24)
        print(f"Found {len(snapshots)} monthly snapshots.")
        
        for idx, snap in enumerate(snapshots, 1):
            ts = snap["timestamp"]
            # Convert timestamp to date YYYY-MM-DD
            asof_date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}"
            print(f"  [{idx}/{len(snapshots)}] Downloading snapshot as of {asof_date}...")
            
            html = download_html(ts, snap["original"])
            if not html:
                print(f"    ⚠️ Failed to download HTML.")
                continue
                
            metrics = parse_consensus_from_html(html)
            if not metrics:
                print(f"    ⚠️ Failed to parse tables from HTML.")
                continue
                
            # Check if we got any valid data
            has_data = any(not np.isnan(v) for v in metrics.values())
            if not has_data:
                print(f"    ⚠️ Parse succeeded but all metrics were NaN.")
                continue
                
            record = {
                "stock_code": code,
                "company_name": name,
                "forecast_asof_date": asof_date,
                **metrics
            }
            all_records.append(record)
            print(f"    ✅ Successfully parsed consensus data.")
            time.sleep(2.0) # rate limit to Wayback server
            
    if not all_records:
        print("No historical snapshots successfully processed.")
        return
        
    # Write to CSV
    df_out = pd.DataFrame(all_records)
    # Reorder columns
    cols = ["stock_code", "company_name", "forecast_asof_date", 
            "earnings_0q_avg", "earnings_1q_avg", "earnings_0y_avg", "earnings_1y_avg",
            "revenue_0q_avg", "revenue_1q_avg", "revenue_0y_avg", "revenue_1y_avg"]
    df_out = df_out[cols]
    
    # Save output
    df_out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"\nFinished! Wrote {len(df_out)} historical records to {OUTPUT_CSV}")
    
    # ----------------------------------------------------
    # Automatically Merge & Deduplicate into biztrends.TW
    # ----------------------------------------------------
    biztrends_target_csv = os.path.abspath(os.path.join(
        REPO_ROOT, "..", "biztrends.TW", "data", "Yahoo.Finance", "raw_yahoo_finance_consensus_history.csv"
    ))
    
    if os.path.exists(biztrends_target_csv):
        print(f"Target history file found: {biztrends_target_csv}")
        try:
            df_old = pd.read_csv(biztrends_target_csv, encoding="utf-8")
            
            # Ensure stock_code is string type in both
            df_old["stock_code"] = df_old["stock_code"].astype(str).str.strip()
            df_out["stock_code"] = df_out["stock_code"].astype(str).str.strip()
            
            # Concat
            df_combined = pd.concat([df_old, df_out], ignore_index=True)
            
            # Drop duplicates by stock_code and forecast_asof_date
            df_combined = df_combined.drop_duplicates(subset=["stock_code", "forecast_asof_date"], keep="last")
            
            # Sort by stock_code and forecast_asof_date
            df_combined = df_combined.sort_values(by=["stock_code", "forecast_asof_date"])
            
            # Save back to biztrends.TW
            df_combined.to_csv(biztrends_target_csv, index=False, encoding="utf-8-sig")
            print(f"Successfully merged & deduplicated. Updated history CSV at {biztrends_target_csv} to {len(df_combined)} records.")
        except Exception as e:
            print(f"Failed to merge with target history CSV: {e}")
    else:
        print(f"Target history file NOT found at {biztrends_target_csv}. Copying current output there...")
        try:
            os.makedirs(os.path.dirname(biztrends_target_csv), exist_ok=True)
            df_out.to_csv(biztrends_target_csv, index=False, encoding="utf-8-sig")
            print(f"Copied to {biztrends_target_csv}")
        except Exception as e:
            print(f"Failed to copy to target path: {e}")

if __name__ == "__main__":
    main()
