#!/usr/bin/env python3
"""Build forecast summary and FactSet cross-check from raw Yahoo rows."""

from __future__ import annotations

import csv
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def to_float(value: str) -> Optional[float]:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(str(value).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def format_float(value: Optional[float]) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(round(value, 6))


class ReportGenerator:
    def __init__(self, large_diff_threshold: float = 0.20):
        self.large_diff_threshold = large_diff_threshold

    def generate(self, raw_csv: str, output_csv: str, factset_report: str) -> None:
        raw_rows = self._read_rows(raw_csv)
        factset = self._load_factset(factset_report)
        process_ts = utc_now()
        current_year = datetime.now(timezone.utc).year

        grouped: Dict[Tuple[str, str, str], Dict] = {}
        for row in raw_rows:
            key = (row["stock_code"], row["market"], row["yahoo_symbol"])
            item = grouped.setdefault(key, self._new_summary(row))
            item["download_timestamp"] = max(item.get("download_timestamp", ""), row.get("download_timestamp", ""))
            item["fetch_status"] = self._merge_status(item.get("fetch_status", ""), row.get("fetch_status", ""))
            if row.get("error_message") and not item.get("error_message"):
                item["error_message"] = row["error_message"]
            self._apply_metric(item, row)

        rows = []
        for item in grouped.values():
            self._apply_factset_cross_check(item, factset, current_year)
            item["forecast_asof_date"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            item["process_timestamp"] = process_ts
            rows.append(item)

        fieldnames = self._summary_columns()
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows([{key: row.get(key, "") for key in fieldnames} for row in rows])

    def _read_rows(self, path: str) -> List[Dict[str, str]]:
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _new_summary(self, row: Dict[str, str]) -> Dict:
        return {
            "stock_code": row.get("stock_code", ""),
            "company_name": row.get("company_name", ""),
            "market": row.get("market", ""),
            "yahoo_symbol": row.get("yahoo_symbol", ""),
            "symbol_resolution_status": row.get("symbol_resolution_status", ""),
            "concept_name": row.get("concept_name", ""),
            "source_url": row.get("source_url", ""),
            "fetch_status": "",
            "error_message": "",
            "download_timestamp": "",
            "next_investor_event_date": "",
            "days_to_investor_event": "",
        }

    def _apply_metric(self, item: Dict, row: Dict[str, str]) -> None:
        section = row.get("section", "")
        period = row.get("period", "")
        metric = row.get("metric", "")
        value = to_float(row.get("value", ""))

        if section == "盈利預估" and metric == "avg":
            if period == "0q":
                item["earnings_0q_avg"] = format_float(value)
            elif period == "+1q":
                item["earnings_1q_avg"] = format_float(value)
            elif period == "0y":
                item["earnings_0y_avg"] = format_float(value)
            elif period == "+1y":
                item["earnings_1y_avg"] = format_float(value)
        elif section == "收益預估" and metric == "avg":
            if period == "0q":
                item["revenue_0q_avg"] = format_float(value)
            elif period == "+1q":
                item["revenue_1q_avg"] = format_float(value)
            elif period == "0y":
                item["revenue_0y_avg"] = format_float(value)
            elif period == "+1y":
                item["revenue_1y_avg"] = format_float(value)
        elif section == "預計增長" and metric in {"stockTrend", "growth"}:
            if period in {"+5y", "0y", ""}:
                item["growth_5y_stock"] = format_float(value)
        elif section == "每股盈利修改":
            if period == "0q" and metric == "upLast7days":
                item["eps_revision_0q_up_7d"] = format_float(value)
            elif period == "0q" and metric == "downLast7days":
                item["eps_revision_0q_down_7d"] = format_float(value)
        elif section == "盈利記錄":
            if metric == "epsEstimate":
                item["last_eps_estimate"] = format_float(value)
                item["last_earnings_date"] = period
            elif metric == "epsActual":
                item["last_eps_actual"] = format_float(value)
                item.setdefault("last_earnings_date", period)

    def _load_factset(self, path: str) -> Dict[str, Dict[str, str]]:
        rows = self._read_rows(path)
        out = {}
        for row in rows:
            code = (row.get("代號") or "").strip()
            if code and code not in out:
                out[code] = row
        return out

    def _apply_factset_cross_check(self, item: Dict, factset: Dict[str, Dict[str, str]], current_year: int) -> None:
        factset_row = factset.get(item["stock_code"])
        if not factset:
            item.update({"factset_available": "false", "cross_check_status": "missing_factset_source", "cross_check_notes": "FactSet report not found"})
            self._forecast_signal(item)
            return
        if not factset_row:
            item.update({"factset_available": "false", "cross_check_status": "missing_factset", "cross_check_notes": "Symbol not found in FactSet report"})
            self._forecast_signal(item)
            return

        item["factset_available"] = "true"
        item["factset_md_latest_date"] = factset_row.get("MD最新日期", "")
        item["factset_quality_score"] = factset_row.get("品質評分", "")

        mappings = [
            ("earnings_0y_avg", f"{current_year}EPS平均值", "factset_eps_current_year_avg", "eps_current_year", False),
            ("earnings_1y_avg", f"{current_year + 1}EPS平均值", "factset_eps_next_year_avg", "eps_next_year", False),
            ("revenue_0y_avg", f"{current_year}營收平均值", "factset_revenue_current_year_avg", "revenue_current_year", True),
            ("revenue_1y_avg", f"{current_year + 1}營收平均值", "factset_revenue_next_year_avg", "revenue_next_year", True),
        ]
        large = False
        notes = []
        revenue_scales = []
        for yahoo_key, factset_key, out_key, prefix, is_revenue in mappings:
            yahoo_value = to_float(item.get(yahoo_key, ""))
            factset_value = to_float(factset_row.get(factset_key, ""))
            if is_revenue:
                factset_value, scale = self._normalize_revenue_scale(yahoo_value, factset_value)
                if scale is not None:
                    revenue_scales.append(f"{prefix}={scale:g}")
            item[out_key] = format_float(factset_value)
            diff, diff_pct = self._diff(yahoo_value, factset_value)
            item[f"{prefix}_diff"] = format_float(diff)
            item[f"{prefix}_diff_pct"] = format_float(diff_pct)
            if diff_pct is not None and abs(diff_pct) > self.large_diff_threshold:
                large = True
                notes.append(f"{prefix} diff_pct={round(diff_pct, 4)}")

        item["cross_check_status"] = "large_diff" if large else "matched"
        item["cross_check_notes"] = "; ".join(notes)
        item["factset_revenue_scale_applied"] = "; ".join(revenue_scales)
        self._forecast_signal(item)

    def _diff(self, yahoo_value: Optional[float], factset_value: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
        if yahoo_value is None or factset_value in (None, 0):
            return None, None
        diff = yahoo_value - factset_value
        return diff, diff / factset_value

    def _normalize_revenue_scale(self, yahoo_value: Optional[float], factset_value: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
        if yahoo_value is None or factset_value in (None, 0):
            return factset_value, None
        candidates = [1.0, 1000.0, 1000000.0, 0.001, 0.000001]
        best_scale = min(
            candidates,
            key=lambda scale: abs((yahoo_value - factset_value * scale) / (factset_value * scale)),
        )
        return factset_value * best_scale, best_scale

    def _forecast_signal(self, item: Dict) -> None:
        if item.get("fetch_status") not in {"success", ""}:
            item["forecast_signal_status"] = "missing"
            item["forecast_confidence"] = "0"
        elif item.get("cross_check_status") == "large_diff":
            item["forecast_signal_status"] = "large_diff"
            item["forecast_confidence"] = "60"
        elif item.get("cross_check_status") == "matched":
            item["forecast_signal_status"] = "fresh"
            item["forecast_confidence"] = "85"
        else:
            item["forecast_signal_status"] = "fresh"
            item["forecast_confidence"] = "70"

    def _merge_status(self, current: str, new: str) -> str:
        if current == "success" or new == "success":
            return "success"
        return current or new

    def _summary_columns(self) -> List[str]:
        return [
            "stock_code", "company_name", "market", "yahoo_symbol", "symbol_resolution_status",
            "concept_name", "source_url", "forecast_asof_date", "next_investor_event_date",
            "days_to_investor_event", "earnings_0q_avg", "earnings_1q_avg", "earnings_0y_avg",
            "earnings_1y_avg", "revenue_0q_avg", "revenue_1q_avg", "revenue_0y_avg",
            "revenue_1y_avg", "growth_5y_stock", "eps_revision_0q_up_7d",
            "eps_revision_0q_down_7d", "last_earnings_date", "last_eps_estimate",
            "last_eps_actual", "factset_available", "factset_md_latest_date",
            "factset_quality_score", "factset_eps_current_year_avg", "eps_current_year_diff",
            "eps_current_year_diff_pct", "factset_eps_next_year_avg", "eps_next_year_diff",
            "eps_next_year_diff_pct", "factset_revenue_current_year_avg",
            "revenue_current_year_diff", "revenue_current_year_diff_pct",
            "factset_revenue_next_year_avg", "revenue_next_year_diff",
            "revenue_next_year_diff_pct", "factset_revenue_scale_applied",
            "cross_check_status", "cross_check_notes",
            "forecast_signal_status", "forecast_confidence", "fetch_status", "error_message",
            "download_timestamp", "process_timestamp",
        ]
