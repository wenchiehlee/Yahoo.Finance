---
source: https://raw.githubusercontent.com/wenchiehlee-investment/ConceptStocks/refs/heads/main/raw_column_definition.md
destination: https://raw.githubusercontent.com/wenchiehlee-investment/Python-Actions.GoodInfo.Analyzer/refs/heads/main/definitions/raw_column_definition_ConceptStocks.md
---

# Raw CSV Column Definitions - ConceptStocks v1.0.0
## US Concept Stock Financials & Segments

## raw_conceptstock_daily.csv (Daily Concept Stock Prices)
**No:** 30
**Source:** Alpha Vantage `TIME_SERIES_DAILY`
**Extraction Strategy:** Use Alpha Vantage daily series (compact for incremental updates). Compute change vs prior close.

### Columns

| Column | Type | Description | Source Field | Notes |
|--------|------|-------------|--------------|-------|
| `交易日期` | date | Trading date | Time Series key | `YYYY-MM-DD` |
| `開盤_價格_元` | float | Open price (USD) | `1. open` | Native daily open |
| `收盤_價格_元` | float | Close price (USD) | `4. close` | Native daily close |
| `漲跌_價格_元` | float | Price change (USD) | Derived | `收盤_價格_元 - 上一日收盤_價格_元` |
| `漲跌_pct` | float | Price change (%) | Derived | `漲跌_價格_元 / 上一日收盤_價格_元` |

---

## raw_conceptstock_weekly.csv (Weekly Concept Stock Prices)
**No:** 31
**Source:** Alpha Vantage `TIME_SERIES_WEEKLY`
**Extraction Strategy:** Use native weekly series. Compute change vs prior week close.

### Columns

| Column | Type | Description | Source Field | Notes |
|--------|------|-------------|--------------|-------|
| `交易週` | date | Week ending date | Time Series key | `YYYY-MM-DD` (week end) |
| `開盤_價格_元` | float | Open price (USD) | `1. open` | Native weekly open |
| `收盤_價格_元` | float | Close price (USD) | `4. close` | Native weekly close |
| `漲跌_價格_元` | float | Price change (USD) | Derived | `收盤_價格_元 - 上一週收盤_價格_元` |
| `漲跌_pct` | float | Price change (%) | Derived | `漲跌_價格_元 / 上一週收盤_價格_元` |

---

## raw_conceptstock_monthly.csv (Monthly Concept Stock Prices)
**No:** 32
**Source:** Alpha Vantage `TIME_SERIES_MONTHLY`
**Extraction Strategy:** Use native monthly series. Compute change vs prior month close.

### Columns

| Column | Type | Description | Source Field | Notes |
|--------|------|-------------|--------------|-------|
| `交易月份` | string | Trading month | Time Series key | `YYYY-MM` |
| `開盤_價格_元` | float | Open price (USD) | `1. open` | Native monthly open |
| `收盤_價格_元` | float | Close price (USD) | `4. close` | Native monthly close |
| `漲跌_價格_元` | float | Price change (USD) | Derived | `收盤_價格_元 - 上一月收盤_價格_元` |
| `漲跌_pct` | float | Price change (%) | Derived | `漲跌_價格_元 / 上一月收盤_價格_元` |

---

## raw_conceptstock_company_revenue.csv (Concept Stock Company Segment Revenue)
**No:** 33
**Source:** Financial Modeling Prep (FMP) or SEC EDGAR (10-K HTML parsing)
**Extraction Strategy:** Fetch product/geographic segment revenue from FMP API (primary) or parse SEC 10-K HTML tables (fallback for ORCL/MU/WDC/QCOM/DELL).

### Columns

| Column | Type | Description | Source Field | Notes |
|--------|------|-------------|--------------|-------|
| `fiscal_year` | integer | Fiscal year | API response | e.g., `2025` |
| `end_date` | date | Fiscal period end date | API response | `YYYY-MM-DD` |
| `period` | string | Period type | API response | `annual` |
| `segment_name` | string | Segment name | API response | e.g., `Intelligent Cloud` |
| `segment_type` | string | Segment category | API response | `product` or `geography` |
| `revenue` | float | Revenue (USD) | API response | Raw value in USD |
| `revenue_yoy_pct` | float | Year-over-year growth | Derived | Decimal format (0.29 = 29%) |
| `currency` | string | Currency code | API response | Always `USD` |
| `source` | string | Data source | System | `FMP` or `SEC` |

---

## raw_conceptstock_company_income.csv (Concept Stock Company Income Statement)
**No:** 34
**Source:** SEC EDGAR XBRL (primary) + Alpha Vantage / FMP (cross-check)
**Extraction Strategy:** Fetch income statement from SEC EDGAR XBRL API (primary). Cross-check with Alpha Vantage and FMP.

### Columns

| Column | Type | Description | Source Field | Notes |
|--------|------|-------------|--------------|-------|
| `fiscal_year` | integer | Fiscal year | API response | e.g., `2025` |
| `end_date` | date | Fiscal period end date | API response | `YYYY-MM-DD` |
| `period` | string | Period type | API response | `FY`, `Q1`, `Q2`, `Q3` |
| `total_revenue` | float | Total revenue (USD) | API response | Top-line revenue |
| `gross_profit` | float | Gross profit (USD) | API response/Derived | Revenue - COGS; derived from `total_revenue - cost_of_revenue` if GrossProfit XBRL unavailable |
| `cost_of_revenue` | float | Cost of revenue (USD) | API response | XBRL: CostOfRevenue/CostOfGoodsAndServicesSold; `null` if unavailable |
| `operating_income` | float | Operating income (USD) | API response | EBIT |
| `net_income` | float | Net income (USD) | API response | Bottom-line profit |
| `eps` | float | Earnings per share | API response | Diluted EPS |
| `gross_margin` | float | Gross margin | Derived | `gross_profit / total_revenue` |
| `operating_margin` | float | Operating margin | Derived | `operating_income / total_revenue` |
| `net_margin` | float | Net margin | Derived | `net_income / total_revenue` |
| `revenue_yoy_pct` | float | Revenue YoY growth rate | Derived | Decimal format (0.25 = 25%); `null` if prior year unavailable |
| `currency` | string | Currency code | API response | Always `USD` |
| `source` | string | Data source | System | `SEC`, `SEC_6K`, `AlphaVantage`, `FMP` |

---

## raw_conceptstock_company_quarterly_segments.csv (Quarterly Product Segment Revenue)
**No:** 35
**Source:** SEC EDGAR 10-Q (Q1-Q3) and 8-K press releases (all quarters)
**Extraction Strategy:** Parse segment revenue from SEC 10-Q filings and 8-K press releases. Q4 is calculated as FY - (Q1+Q2+Q3).

### Columns

| Column | Type | Description | Source Field | Notes |
|--------|------|-------------|--------------|-------|
| `fiscal_year` | integer | Fiscal year | Parsed | e.g., `2026` |
| `quarter` | string | Fiscal quarter | Parsed | `Q1`, `Q2`, `Q3`, `Q4` |
| `segment_name` | string | Product segment name | Parsed | e.g., `Data Center`, `Gaming` |
| `revenue` | float | Segment revenue (USD) | Parsed | Raw value in USD; `null` if only % available |
| `end_date` | date | Quarter end date | Parsed | `YYYY-MM-DD` |
| `is_calculated` | boolean | Whether Q4 was calculated | System | `True` if Q4 = FY-(Q1+Q2+Q3) |
| `download_timestamp` | datetime | Source data retrieval timestamp | System | UTC `YYYY-MM-DD HH:MM:SS` |
| `process_timestamp` | datetime | CSV generation timestamp | System | UTC `YYYY-MM-DD HH:MM:SS` |

---

## raw_conceptstock_company_segment_overrides.csv (Manual Segment Revenue Overrides)
**No:** 36
**Source:** Manual entry from 10-K filings
**Extraction Strategy:** Hand-curated data to fill gaps or fix errors in FMP/SEC automated parsing.

### Columns

| Column | Type | Description | Source Field | Notes |
|--------|------|-------------|--------------|-------|
| `symbol` | string | Company ticker | Manual | e.g., `NVDA` |
| `fiscal_year` | integer | Fiscal year | Manual | e.g., `2025` |
| `period` | string | Fiscal period | Manual | `annual` |
| `segment_name` | string | Segment name | Manual | e.g., `Gaming` |
| `segment_type` | string | Segment category | Manual | `product` or `geography` |
| `revenue` | float | Segment revenue (USD) | Manual | Raw value in USD |
| `source` | string | Source filing | Manual | e.g., `10-K` |
| `notes` | string | Manual override rationale | Manual | Free text |
| `updated_timestamp` | datetime | Manual row update timestamp | Manual/System | UTC `YYYY-MM-DD HH:MM:SS` |

---

## raw_conceptstock_company_metadata.csv (Concept Stock Company Metadata)
**No:** 37
**Source:** Concept mapping sync (`--sync-concepts`) and maintained metadata table
**Extraction Strategy:** Store concept-to-company metadata used for ticker resolution, CIK mapping, report tracking, and README concept table generation.

### Columns

| Column | Type | Description | Source Field | Notes |
|--------|------|-------------|--------------|-------|
| `概念欄位` | string | Concept column name | System | e.g., `nVidia概念`, `TSMC概念` |
| `公司名稱` | string | Company display name | Metadata | e.g., `NVIDIA Corporation` |
| `Ticker` | string | Query ticker symbol | Metadata | US ticker or ADR preferred |
| `CIK` | string | SEC CIK identifier | Metadata | e.g., `0001045810` |
| `最新財報` | string | Latest released fiscal report | Metadata | e.g., `FY2026 Q3` |
| `發布時間` | string | Expected release timing | Metadata | e.g., `2026年4月` |
| `產品區段` | string | Product segment summary | Metadata | Free text |
| `download_timestamp` | datetime | Source metadata retrieval timestamp | System | UTC `YYYY-MM-DD HH:MM:SS` |
| `process_timestamp` | datetime | CSV generation timestamp | System | UTC `YYYY-MM-DD HH:MM:SS` |
