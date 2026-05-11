#!/usr/bin/env python3
"""Generate Yahoo Finance forecast summary from long-format raw CSV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from process_group.report_generator import ReportGenerator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--raw-csv")
    parser.add_argument("--output-csv")
    parser.add_argument("--factset-report")
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    raw_csv = args.raw_csv or config["output"]["raw_csv"]
    output_csv = args.output_csv or config["output"]["summary_csv"]
    factset_report = args.factset_report or config["cross_check"]["factset_report"]
    threshold = float(config["cross_check"].get("large_diff_pct_threshold", 0.20))

    ReportGenerator(threshold).generate(raw_csv, output_csv, factset_report)
    print(f"Wrote summary to {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
