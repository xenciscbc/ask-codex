# 安全演練 skill：grilling 共識筆記（暫存，不是 spec）

Status: on hold — 2026-10-13 grilling 的決定；spec 暫不撰寫（使用者決定）。共用部分（演練、可丟棄目標、事前檢查、命令列固定值）以 `spec.md`（UI 演練）為準。

| # | 決定 |
|---|---|
| Q5、Q31 | user-only：`/ask-codex:security [model] <範圍>`，範圍必填 |
| Q3 | Codex 在可丟棄目標上以 `workspace-write` 自行執行證明 |
| Q4 | 範圍：程式碼（路徑、功能、diff）＋ Claude 從可丟棄目標啟動的 localhost port；不含外部服務 |
| Q9 | 每個論點由 Claude 在同一可丟棄目標上重現；成功才標「已證實」，否則「未證實」 |
| Q15 | 只報告，不修 |
| Q16 | 證據預設隨目標刪除；使用者要求時搬到使用者指定位置 |
| Q18 | 範圍外只列為「範圍外，未測試」 |
| Q19 | 網路事前檢查：localhost 可達、外部不可達，否則中止；結果依設定指紋沿用 12 小時（Q23'） |
| Q24 | 範圍含 web 前端時可用與 UI 演練相同的受限瀏覽器 |
| Q29' | Codex shell 可連本機所有 loopback port（Codex 設定擋不住，P8c）→ 只在 README 註明 |
| Q32 | 命令列固定 `approval_policy="never"`（approval-boundary/01） |

證據：`probe-results.md`（P2、P8、P9）。
