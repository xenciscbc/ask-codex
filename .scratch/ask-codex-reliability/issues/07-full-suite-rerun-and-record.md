# 07 — 全套重跑與紀錄校正

**What to build:** 69 案例套件在 HEAD 重跑，每個案例的證據都對應到現行 bytes；排除三個刻意的 control 後全綠；專案紀錄（PLAN.md 的覆蓋範圍縮窄註記、MVP spec 的已知缺陷）更新為真實狀態。這是合併回 `main` 前的最後一張。

**Blocked by:** 04、05、06.

**Status:** ready-for-agent

## 要做的事

1. WSL 內先確認 Claude 登入有效，再以一次 `run-evals.sh` 跑全套（不分批、不並行），`--allow-tools Bash Write TaskOutput TaskStop`。
2. 讀 `aggregate-result.json`：`diagnosis-leak-control` 的 `no-hypothesis` 必須失敗（red-phase control）；`history-probe-nofixture` 與 `task-tools-probe` 是 harness probe；其餘全部 1.00。
3. 任一非 control 案例未達 1.00：先判斷是 grader 問題還是 skill 退步；退步則回到對應 ticket 修正並重跑受影響案例，不在本 ticket 內改 skill。
4. 更新 `.scratch/ask-codex-mvp/plan/PLAN.md` 的覆蓋範圍縮窄註記為「已於 <commit> 全套重跑」，MVP spec 或 README 中的已知缺陷清單移除 12、14–17。

## Acceptance criteria

- [ ] 全套重跑結果檔存在，非 control 案例 66 個全部 1.00；三個 control 的行為如上。
- [ ] 重跑的 commit 與 skill、腳本、eval 的最終 bytes 相同（fingerprint：HEAD 加工作樹 diff 為空）。
- [ ] PLAN.md 與 MVP 紀錄更新，不再宣稱「60 個案例證據早於現行 bytes」。
- [ ] 費用與耗時記在本 ticket 的 Comments。
- [ ] 本 feature 的分支已可合併回 `main`（合併與 push 等使用者指示）。
