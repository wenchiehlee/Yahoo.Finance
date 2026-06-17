#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download Taiwan observation and focus lists using the same mechanism as
GoogleSearch.Factset.
"""

import os
from datetime import datetime

import requests


BASE_URL = "https://raw.githubusercontent.com/wenchiehlee/Selenium-Actions.Auction/refs/heads/main"


def download_file(url, output_file, description, add_taiex=False):
    try:
        print(f"正在下載 {description}...")
        print(f"來源: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.content.decode("utf-8")

        if add_taiex and "0000,台灣加權指數" not in content:
            if not content.endswith("\n"):
                content += "\n"
            content += "0000,台灣加權指數\n"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"成功儲存 {description}: {output_file} ({os.path.getsize(output_file):,} bytes)")
        return True
    except Exception as exc:
        print(f"{description} 下載失敗: {exc}")
        return False


def main():
    print("=" * 60)
    print(f"台灣股市名單下載程式: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    success_obs = download_file(
        f"{BASE_URL}/%E8%A7%80%E5%AF%9F%E5%90%8D%E5%96%AE.csv",
        "StockID_TWSE_TPEX.csv",
        "觀察名單",
        add_taiex=True,
    )
    success_focus = download_file(
        f"{BASE_URL}/%E5%B0%88%E6%B3%A8%E5%90%8D%E5%96%AE.csv",
        "StockID_TWSE_TPEX_focus.csv",
        "專注名單",
        add_taiex=False,
    )

    if not (success_obs and success_focus):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
