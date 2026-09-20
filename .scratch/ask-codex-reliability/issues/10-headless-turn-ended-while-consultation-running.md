# 10 — headless session 在諮詢還在跑時結束了 turn

**What to build:** `claude -p` 的諮詢從啟動到呈現都在同一個 turn 內完成；skill step 8 的「Do not end your turn while the consultation is still running」在沒有 `TaskOutput` 阻塞、改用背景計時器等待的路徑上也成立。

**Blocked by:** 無。**Status:** needs-triage

## Evidence（2026-09-20，ticket 04 的 headless 試跑 H2，真實 Codex）

- 最後一個 assistant 文字區塊是「Codex 已在背景執行，計時器（1 分鐘）已啟動，等待其中一個完成通知。」，之後沒有任何工具呼叫；stream-json 結尾是兩個 `task_updated … "status":"killed"`（諮詢 task 與計時器），也就是 session 結束時 harness 收掉了它們。
- Codex 在約 38 秒後自行完成（`last-message.json` 出現），但沒有人讀它：沒有 step 9/10，沒有 step 11。
- 行程鏈在 session 結束時消失（watcher：leaf 64 s、`last-message` 102.7 s、chain gone 113.1 s），沒有殘留行程、沒有額外配額消耗。
- run directory `R:\Temp\ask-codex\run.BpS1XW` 留在磁碟上，含 `prompt.md`（已由主 session 手動刪除）。
- 同一天第一次 headless（scenario H）沒有發生：那次用 `TaskOutput block:true` 等待。單一觀察，發生率未知。skill bytes：工作樹含 ticket 05 與 08 的改動，兩者都沒有動 step 8。

## 影響

諮詢結果遺失；含程式碼摘錄的 `prompt.md` 留在磁碟上（ticket 13 同類的後果，不同的成因）。

## 下一步

先量發生率：既有的計時器案例（`timeout-*`、`parallel-shared-timer`）在 eval 中都有 `TaskOutput`，量不到這條路徑；需要一個不授予 `TaskOutput` 的 headless 案例，`--runs 5`，grader：`temp-cleanup` 加上最終回覆含 step 10 的 MCP 行。

## Acceptance criteria

- [ ] 有一個能重現（或五跑不重現）的 eval 案例，走背景計時器路徑。
- [ ] 若重現：step 8 的等待指示改到該案例 `--runs 5` 全過；若不重現：以「未重現」結案並記錄。
