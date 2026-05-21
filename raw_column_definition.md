---
source: https://raw.githubusercontent.com/wenchiehlee/Yahoo.Finance/refs/heads/main/raw_column_definition.md
destination: downstream definitions/raw_column_definition_YahooFinance.md
---

# Raw CSV Column Definitions - Yahoo.Finance

## raw_yahoo_finance.csv (Yahoo Finance Analyst Analysis, Long Format)
**No:** TBD
**Source:** `data/stage1_raw/raw_yahoo_finance.csv`
**Data Source:** Yahoo Finance HK analysis page via yfinance
**Update Frequency:** Daily automated updates
**Extraction Strategy:** Fetch structured yfinance analyst analysis tables and normalize them into long format. `source_url` points to the human-readable Yahoo HK analysis page. US ticker universe is read from `data/ConceptStocks/raw_conceptstock_company_metadata.csv`, synced from ConceptStocks.

### Section Mapping

| section | source_method | Yahoo page |
|---|---|---|
| `收益預估` | `get_revenue_estimate` | `/analysis/` |
| `盈利預估` | `get_earnings_estimate` | `/analysis/` |
| `盈利記錄` | `get_earnings_history` | `/analysis/` |
| `每股盈利走勢` | `get_eps_trend` | `/analysis/` |
| `每股盈利修改` | `get_eps_revisions` | `/analysis/` |
| `預計增長` | `get_growth_estimates` | `/analysis/` |

### Columns

| Column | Type | Description | Source Field | Notes |
|---|---|---|---|---|
| `stock_code` | string | Original stock code or ticker | TW list `代號`; ConceptStocks `Ticker` | e.g., `2330`, `NVDA` |
| `company_name` | string | Company display name | TW list `名稱`; ConceptStocks `公司名稱` |  |
| `market` | string | Market code | System | `TW`, `TWO`, `US`, `UNKNOWN` |
| `yahoo_symbol` | string | Yahoo Finance ticker symbol | System | e.g., `2330.TW`, `8299.TWO`, `NVDA` |
| `symbol_resolution_status` | string | Symbol resolution result | System | `resolved`, `fallback_to_two`, `not_found`, `skipped_index`, `skipped_private_or_missing_ticker` |
| `concept_name` | string | ConceptStocks concept name | ConceptStocks `概念欄位` | Blank for Taiwan stocks |
| `source_url` | string | Yahoo HK analysis URL | System | `https://hk.finance.yahoo.com/quote/{yahoo_symbol}/analysis/` |
| `section` | string | Analyst analysis section name | System | Chinese label from section mapping |
| `source_method` | string | yfinance method name | System | See section mapping |
| `period` | string | Forecast period or earnings date | yfinance DataFrame index/column | e.g., `0q`, `+1q`, `0y`, `+1y`, `+5y`, date |
| `metric` | string | Raw metric name | yfinance DataFrame index/column | e.g., `avg`, `low`, `high`, `upLast7days` |
| `metric_zh` | string | Chinese metric label | System | e.g., `平均值`, `最低值`, `近7天上修` |
| `value` | string | Raw metric value | yfinance | Kept as string-compatible numeric text |
| `unit` | string | Value unit classification | System | `eps`, `revenue`, `pct`, `count`, blank |
| `currency` | string | Currency code where applicable | System | `TWD` for TW/TWO, `USD` for US |
| `fetch_status` | string | Fetch row status | System | `success`, `empty`, `error`, `symbol_not_found`, `skipped_index`, `skipped_private_or_missing_ticker` |
| `error_message` | string | Error or skip reason | System | Blank for success rows |
| `source_metadata_timestamp` | datetime | Upstream metadata timestamp | ConceptStocks `process_timestamp` | Used for US metadata provenance |
| `download_timestamp` | datetime | Yahoo/yfinance retrieval timestamp | System | UTC `YYYY-MM-DD HH:MM:SS` |
| `process_timestamp` | datetime | CSV generation timestamp | System | UTC `YYYY-MM-DD HH:MM:SS` |

---

## raw_yahoo_finance_summary_latest.csv (Yahoo Finance Forecast Summary)

**Source:** `data/forecast/raw_yahoo_finance_summary_latest.csv`
**Data Source:** `raw_yahoo_finance.csv` plus synced FactSet detailed report
**Update Frequency:** Daily automated updates
**Extraction Strategy:** Pivot selected Yahoo metrics into one row per symbol, then cross-check current/next-year EPS and revenue estimates against `raw_factset_detailed_report.csv`.

### Columns

| Column | Type | Description | Source Field | Notes |
|---|---|---|---|---|
| `stock_code` | string | Original stock code or ticker | raw Yahoo | Primary symbol |
| `company_name` | string | Company display name | raw Yahoo |  |
| `market` | string | Market code | raw Yahoo | `TW`, `TWO`, `US` |
| `yahoo_symbol` | string | Yahoo Finance ticker symbol | raw Yahoo |  |
| `symbol_resolution_status` | string | Symbol resolution result | raw Yahoo |  |
| `concept_name` | string | ConceptStocks concept name | raw Yahoo | Blank for Taiwan stocks |
| `source_url` | string | Yahoo HK analysis URL | raw Yahoo | Human review link |
| `forecast_asof_date` | date | Forecast snapshot date | System | UTC date |
| `next_investor_event_date` | date | Next investor event date | Future integration | Blank in first version |
| `days_to_investor_event` | integer | Days until next investor event | Future integration | Blank in first version |
| `earnings_0q_avg` | float | Current-quarter average EPS estimate | Yahoo `盈利預估` | period `0q`, metric `avg` |
| `earnings_1q_avg` | float | Next-quarter average EPS estimate | Yahoo `盈利預估` | period `+1q`, metric `avg` |
| `earnings_0y_avg` | float | Current-year average EPS estimate | Yahoo `盈利預估` | period `0y`, metric `avg` |
| `earnings_1y_avg` | float | Next-year average EPS estimate | Yahoo `盈利預估` | period `+1y`, metric `avg` |
| `revenue_0q_avg` | float | Current-quarter average revenue estimate | Yahoo `收益預估` | period `0q`, metric `avg` |
| `revenue_1q_avg` | float | Next-quarter average revenue estimate | Yahoo `收益預估` | period `+1q`, metric `avg` |
| `revenue_0y_avg` | float | Current-year average revenue estimate | Yahoo `收益預估` | period `0y`, metric `avg` |
| `revenue_1y_avg` | float | Next-year average revenue estimate | Yahoo `收益預估` | period `+1y`, metric `avg` |
| `growth_5y_stock` | float | Long-term growth estimate | Yahoo `預計增長` | Usually period `+5y` |
| `eps_revision_0q_up_7d` | float | Current-quarter EPS estimate upward revisions in last 7 days | Yahoo `每股盈利修改` |  |
| `eps_revision_0q_down_7d` | float | Current-quarter EPS estimate downward revisions in last 7 days | Yahoo `每股盈利修改` |  |
| `last_earnings_date` | date/string | Latest earnings history period | Yahoo `盈利記錄` |  |
| `last_eps_estimate` | float | Latest historical EPS estimate | Yahoo `盈利記錄` |  |
| `last_eps_actual` | float | Latest historical EPS actual | Yahoo `盈利記錄` |  |
| `factset_available` | boolean | Whether FactSet row is available | FactSet report |  |
| `factset_md_latest_date` | date | Latest FactSet markdown date | FactSet `MD最新日期` |  |
| `factset_quality_score` | float | FactSet quality score | FactSet `品質評分` |  |
| `factset_eps_current_year_avg` | float | FactSet current-year EPS average | FactSet `{YYYY}EPS平均值` | `YYYY` is execution year |
| `eps_current_year_diff` | float | Yahoo current-year EPS minus FactSet | Derived |  |
| `eps_current_year_diff_pct` | float | Current-year EPS percentage difference | Derived | `(Yahoo - FactSet) / FactSet` |
| `factset_eps_next_year_avg` | float | FactSet next-year EPS average | FactSet `{YYYY+1}EPS平均值` |  |
| `eps_next_year_diff` | float | Yahoo next-year EPS minus FactSet | Derived |  |
| `eps_next_year_diff_pct` | float | Next-year EPS percentage difference | Derived |  |
| `factset_revenue_current_year_avg` | float | FactSet current-year revenue average normalized to Yahoo comparison scale | FactSet `{YYYY}營收平均值` + scale normalization |  |
| `revenue_current_year_diff` | float | Yahoo current-year revenue minus FactSet | Derived |  |
| `revenue_current_year_diff_pct` | float | Current-year revenue percentage difference | Derived |  |
| `factset_revenue_next_year_avg` | float | FactSet next-year revenue average normalized to Yahoo comparison scale | FactSet `{YYYY+1}營收平均值` + scale normalization |  |
| `revenue_next_year_diff` | float | Yahoo next-year revenue minus FactSet | Derived |  |
| `revenue_next_year_diff_pct` | float | Next-year revenue percentage difference | Derived |  |
| `factset_revenue_scale_applied` | string | Revenue scale factors applied to FactSet values before Yahoo comparison | Derived | e.g., `revenue_current_year=1000; revenue_next_year=1000` |
| `cross_check_status` | string | Yahoo vs FactSet comparison status | Derived | `matched`, `missing_factset_source`, `missing_factset`, `large_diff` |
| `cross_check_notes` | string | Cross-check notes | Derived |  |
| `forecast_signal_status` | string | Forecast signal status | Derived | `fresh`, `missing`, `large_diff` |
| `forecast_confidence` | float | Forecast confidence score | Derived | 0-100 |
| `fetch_status` | string | Overall Yahoo fetch status | raw Yahoo |  |
| `error_message` | string | Error or skip reason | raw Yahoo |  |
| `download_timestamp` | datetime | Latest Yahoo/yfinance retrieval timestamp | raw Yahoo | UTC |
| `process_timestamp` | datetime | Summary generation timestamp | System | UTC |
