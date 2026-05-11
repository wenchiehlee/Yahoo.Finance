---
source: https://raw.githubusercontent.com/wenchiehlee/GoogleSearch.Factset/refs/heads/main/raw_column_definition.md
destination: https://raw.githubusercontent.com/wenchiehlee-investment/Python-Actions.GoodInfo.Analyzer/refs/heads/main/definitions/raw_column_definition_Factset.md
---

## raw_factset_detailed_report.csv (FactSet Analyst Consensus Summary)
**No:** 51
**Source:** `data/stage1_raw/raw_factset_detailed_report.csv`
**Data Source:** FactSet via GoogleSearch.Factset pipeline
**Update Frequency:** Daily automated updates
**Extraction Strategy:** Pre-aggregated summary data from FactSet analyst consensus reports

### Column Definitions:

| Column | Type | Description | Source | Notes |
|--------|------|-------------|--------|-------|
| `代號` | string | 4-digit stock code | FactSet | Primary key |
| `名稱` | string | Company name in Traditional Chinese | FactSet | Display name |
| `股票代號` | string | Full stock code with market suffix | FactSet | Format: `{code}-TW` (e.g., `2357-TW`) |
| `MD最舊日期` | date | Oldest markdown report date | Metadata | Format: `YYYY-MM-DD` |
| `MD最新日期` | date | Most recent markdown report date | Metadata | Format: `YYYY-MM-DD` |
| `MD資料筆數` | int | Total number of markdown reports available | Metadata | Count of historical reports |
| `分析師數量` | int | Number of analysts covering this stock | FactSet | Higher = better coverage |
| `目標價` | float | Analyst consensus target price (NT$) | FactSet | May be empty if no consensus |
| `2025EPS最高值` | float | EPS highest estimate (N) | FactSet | Available if MD日期=2025 |
| `2025EPS最低值` | float | EPS lowest estimate (N) | FactSet | Available if MD日期=2025 |
| `2025EPS平均值` | float | EPS average estimate (N) | FactSet | Available if MD日期=2025 |
| `2026EPS最高值` | float | EPS highest estimate (N+1 or N) | FactSet | N+1 (2025 report) / N (2026 report) |
| `2026EPS最低值` | float | EPS lowest estimate (N+1 or N) | FactSet | Bear case scenario N+1 (2025 report) / N (2026 report)|
| `2026EPS平均值` | float | EPS average estimate (N+1 or N) | FactSet | Consensus estimate N+1 (2025 report) / N (2026 report)|
| `2027EPS最高值` | float | EPS highest estimate (N+2 or N+1) | FactSet | N+2 (2025 report) / N+1 (2026 report) |
| `2027EPS最低值` | float | EPS lowest estimate (N+2 or N+1) | FactSet | Bear case scenario N+2 (2025 report) / N+1 (2026 report)|
| `2027EPS平均值` | float | EPS average estimate (N+2 or N+1) | FactSet | Consensus estimate N+2 (2025 report) / N+1 (2026 report)|
| `2028EPS最高值` | float | EPS highest estimate (N+2) | FactSet | Available if MD日期=2026 |
| `2028EPS最低值` | float | EPS lowest estimate (N+2) | FactSet | Available if MD日期=2026 |
| `2028EPS平均值` | float | EPS average estimate (N+2) | FactSet | Available if MD日期=2026 |
| `2025營收最高值` | float | Revenue highest estimate (N) | FactSet | Available if MD日期=2025 |
| `2025營收最低值` | float | Revenue lowest estimate (N) | FactSet | Available if MD日期=2025 |
| `2025營收平均值` | float | Revenue average estimate (N) | FactSet | Available if MD日期=2025 |
| `2025營收中位數` | float | Revenue median estimate (N) | FactSet | Available if MD日期=2025 |
| `2026營收最高值` | float | Revenue highest estimate (N+1 or N) | FactSet | N+1 (2025 report) / N (2026 report) |
| `2026營收最低值` | float | Revenue lowest estimate (N+1 or N) | FactSet | Bear case scenario |
| `2026營收平均值` | float | Revenue average estimate (N+1 or N) | FactSet | Consensus estimate |
| `2026營收中位數` | float | Revenue median estimate (N+1 or N) | FactSet | Median consensus |
| `2027營收最高值` | float | Revenue highest estimate (N+2 or N+1) | FactSet | N+2 (2025 report) / N+1 (2026 report) |
| `2027營收最低值` | float | Revenue lowest estimate (N+2 or N+1) | FactSet | Bear case scenario |
| `2027營收平均值` | float | Revenue average estimate (N+2 or N+1) | FactSet | Consensus estimate |
| `2027營收中位數` | float | Revenue median estimate (N+2 or N+1) | FactSet | Median consensus |
| `2028營收最高值` | float | Revenue highest estimate (N+2) | FactSet | Available if MD日期=2026 |
| `2028營收最低值` | float | Revenue lowest estimate (N+2) | FactSet | Available if MD日期=2026 |
| `2028營收平均值` | float | Revenue average estimate (N+2) | FactSet | Available if MD日期=2026 |
| `2028營收中位數` | float | Revenue median estimate (N+2) | FactSet | Available if MD日期=2026 |
| `品質評分` | float | Data quality score (0.0-10.0) | Calculated | Based on completeness & coverage |
| `狀態` | string | Quality status with emoji indicator | Calculated | `🟢 優秀`, `🟡 良好`, `🟠 普通`, `🔴 不足` |
| `MD日期` | date | Primary markdown report reference date | Metadata | Format: `YYYY-MM-DD` |
| `MD File` | string | URL to detailed analyst report markdown | GitHub | Full URL to raw markdown file |
| `搜尋日期` | datetime | When data was searched/fetched | Metadata | Format: `YYYY-MM-DD HH:MM:SS` |
| `處理日期` | datetime | When data was processed/aggregated | Metadata | Format: `YYYY-MM-DD HH:MM:SS` |
| `download_timestamp` | datetime | Source data retrieval timestamp | System | Format: `YYYY-MM-DD HH:MM:SS` |
| `process_timestamp` | datetime | CSV generation timestamp | System | Format: `YYYY-MM-DD HH:MM:SS` |
