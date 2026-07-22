# raw_yahoo_finance_consensus_history.csv 欄位定義說明 (Column Definition)

本文件定義由 `Yahoo.Finance` 倉庫抽取並同步至此倉庫的分析師共識歷史數據庫欄位結構：

| 欄位名稱 (Column) | 資料型態 (Type) | 說明 (Description) |
| :--- | :--- | :--- |
| `stock_code` | `string` | 股票代碼 (例如：`2330` 代表台積電，`2382` 代表廣達) |
| `company_name` | `string` | 公司名稱 (例如：`台積電`、`廣達`) |
| `forecast_asof_date` | `date` | 共識資料基準日期，格式為 `YYYY-MM-DD` |
| `earnings_0q_avg` | `float` | 分析師對**當前未公佈季度 ($Q_0$)** 的平均 EPS 預估值 |
| `earnings_1q_avg` | `float` | 分析師對**下一季度 ($Q_1$)** 的平均 EPS 預估值 |
| `earnings_0y_avg` | `float` | 分析師對**當前會計年度 ($Y_0$)** 的平均 EPS 預估值 |
| `earnings_1y_avg` | `float` | 分析師對**下一會計年度 ($Y_1$)** 的平均 EPS 預估值 |
| `revenue_0q_avg` | `float` | 分析師對**當前未公佈季度 ($Q_0$)** 的平均營業收入預估值，單位：元 |
| `revenue_1q_avg` | `float` | 分析師對**下一季度 ($Q_1$)** 的平均營業收入預估值，單位：元 |
| `revenue_0y_avg` | `float` | 分析師對**當前會計年度 ($Y_0$)** 的平均營業收入預估值，單位：元 |
| `revenue_1y_avg` | `float` | 分析師對**下一會計年度 ($Y_1$)** 的平均營業收入預估值，單位：元 |
| `process_timestamp` | `datetime` | 此歷史共識資料列寫入或更新時間；freshness 監控使用此欄，而不是歷史內容日期 `forecast_asof_date` |

## 備註說明：
1. **無後窺回測使用法**：在回測歷史月份或季度 $t$ 時，應依據該期財報公告日或營收公告日 $T_{ann}$，過濾 `forecast_asof_date` $\le T_{ann}$ 且最接近的共識紀錄作為預估值。
2. **季度營收單位**：在預報管線中使用時，須將 `revenue_*q_avg` 的值除以 `1e8` 轉換為台灣申報慣用的「億元」單位。
