# 03 — 停止路徑接入 skill 與 eval

**What to build:** 使用者（或 skill 依規則）停止一次諮詢時，skill 走新的停止路徑：先跑停止腳本（kill、驗證、印報告行），再呼叫 `TaskStop`；停止報告行逐字複製自腳本輸出；並行檢查的結果附在模型必然會寫的文字上。eval 能證明 stub 行程真的被結束，而不只是 kill 指令有被下。這張關閉 ticket 12、15、16 的離線部分；使用者可信的保證在 04 完成。

**Blocked by:** 01（決定驗收要驗幾種 session、停止報告缺漏的類型）、02（腳本）.

**Status:** ready-for-agent

## 行為改動（step 8 與 step 10）

- step 8 的啟動指令改為以啟動腳本為前綴，`codex exec …` 與轉導原樣保留在同一行。
- 停止路徑：先停止腳本、後 `TaskStop`（無論 task 是否已自行結束）；停止報告行為腳本印出的那一行，逐字複製到停止當下的訊息，並在 step 10 重述。
- 刪除「行動前先寫 `Parallel check:`」的規則。並行檢查資訊改為：繼續等的通知加上 `; done — …; still running — …`；`AskUserQuestion` 問題正文第一行為 `Parallel check: done — …; still running — …`；停止報告行內含同樣欄位（由腳本印出）。step 10 最終呈現仍逐行列出每次檢查的 `Parallel check:` 行。
- 存活檢查的判準不變（只看 task 狀態與最後事件）。

## Grader 改動

- `timeout-stalled-stop`、`parallel-shared-timer`：新增「`.stub/exec-finished` 不存在」；`stopped-line` 改為驗證完整欄位且含 `process tree ended` 或 `process tree NOT confirmed` 其一。
- `parallel-shared-timer`：刪除 `check-line-before-stop`；新增 trace regex 驗證繼續等通知、問題文字或停止報告含 `done —` 與 `still running —`；`check-line`（最終呈現）保留。
- `used-taskstop`、`one-codex-exec`、`exec-twice`、`two-background-runs`、`temp-cleanup`、`no-bare-cd` 不變且仍須通過。

## Acceptance criteria

- [ ] `timeout-stalled-stop` `--runs 5` 全部 1.00（含新 grader）。
- [ ] `parallel-shared-timer` `--runs 5` 全部 1.00（含新 grader）。
- [ ] 每個 run 的 `.stub/exec-finished` 都不存在，證明 stub 被結束。
- [ ] 沒有任何 run 出現「停止報告缺漏」或「並行檢查資訊缺漏」。
- [ ] 回歸樣本（正常諮詢、失敗路徑、接續諮詢各一個既有案例）仍 1.00，因為 step 8 的啟動指令改了。
- [ ] `claude plugin validate` 通過；harness 的離線 grader 檢查（先例 `check-t11-graders.mjs` 類型的腳本）證明新 regex 對正確回覆通過、對缺欄位的改寫失敗。
- [ ] ticket 08 的 Comments 追加實測可靠度（原本的單次綠燈改記為「三跑二中，於本 ticket 修正後五跑五中」）。
- [ ] 每個 grader 改動與 skill 改動都在 plan-verifier READY 的合約範圍內；完成後由 fresh verifier 對「停止路徑離線成立」這個 claim 給 CONFIRMED。
