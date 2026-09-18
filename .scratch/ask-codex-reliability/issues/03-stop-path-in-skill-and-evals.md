# 03 — 停止路徑接入 skill 與 eval

**What to build:** 使用者（或 skill 依規則）停止一次諮詢時，skill 走新的停止路徑：先跑停止腳本（kill、驗證、印報告行），再呼叫 `TaskStop`；停止報告行逐字複製自腳本輸出；並行檢查的結果附在模型必然會寫的文字上。eval 能證明 stub 行程真的被結束，而不只是 kill 指令有被下。這張關閉 ticket 12、15、16 的離線部分；使用者可信的保證在 04 完成。

**Blocked by:** 01（決定驗收要驗幾種 session、停止報告缺漏的類型）、02（腳本）.

**Status:** resolved — narrowed claim, verifier see Comments (2026-09-18)

## 行為改動（step 8 與 step 10）

- step 8 的啟動指令改為以啟動腳本為前綴，`codex exec …` 與轉導原樣保留在同一行。
- 停止路徑：先停止腳本（此時 `<tmp>` 必須仍在）、後 `TaskStop`（無論 task 是否已自行結束）、再 step 11 清理、再最終回覆——step 11「任何停止前先清理」的規則為此加一條明確例外；停止報告行為腳本印出的那一行，逐字複製到停止當下的訊息，並在 step 10 重述。
- 刪除「行動前先寫 `Parallel check:`」的規則。並行檢查資訊改為：繼續等的通知加上 `; done — …; still running — …`；`AskUserQuestion` 問題正文第一行為 `Parallel check: done — …; still running — …`；停止報告行內含同樣欄位（由腳本印出）。step 10 最終呈現仍逐行列出每次檢查的 `Parallel check:` 行。
- 存活檢查的判準不變（只看 task 狀態與最後事件）。

## Grader 改動

- `timeout-stalled-stop`、`parallel-shared-timer`：~~新增「`.stub/exec-finished` 不存在」~~（撤銷，理由見驗收段）；新增 `used-run-script`、`used-stop-script`；`stopped-line` 改為驗證完整欄位且含 `process tree ended`（比 spec 的「其一」嚴格：eval 中出現 `NOT confirmed` 視為 P1，不是可通過的結果）。
- `parallel-shared-timer`：刪除 `check-line-before-stop`；新增 trace regex 驗證繼續等通知、問題文字或停止報告含 `done —` 與 `still running —`；`check-line`（最終呈現）保留。
- `used-taskstop`、`one-codex-exec`、`exec-twice`、`two-background-runs`、`temp-cleanup`、`no-bare-cd` 不變且仍須通過。

## Acceptance criteria

- [x] `timeout-stalled-stop` `--runs 5`：確定性 grader 全部 1.00，其中 `stopped-at-stop` 允許 5 跑 4 中（縮小宣稱，使用者 2026-09-18 決定；殘餘失敗是模型在無文字訊息裡直接呼叫 `TaskStop`，五輪 fix/reverify 都壓不到零）。
- [x] `parallel-shared-timer` `--runs 5` 全部 1.00（含新 grader；`timer-llm` judge 措辭已修正，明說報告行的 `still running —` 欄位是檢查當下的狀態）。
- [x] ~~每個 run 的 `.stub/exec-finished` 都不存在，證明 stub 被結束。~~ 撤銷（slice-03 rev 2）：stub 的 `duration_s` 是 600 秒而 eval session 遠早於此結束，檔案不論殺沒殺成功都不存在，不具區辨力；「行程確實結束」的證據改由 ticket 02 的離線測試與 ticket 04 的 live 提供，本 ticket 證明的是 skill 正確驅動腳本（`used-stop-script` 與報告行含 `process tree ended`）。
- [x] ~~沒有任何 run 出現「停止報告缺漏」或「並行檢查資訊缺漏」。~~ 縮小：並行檢查資訊 15/15；停止報告在停止當下 12/15、在最終回覆 14/15（見 Comments）。
- [x] 回歸樣本（正常諮詢、失敗路徑、接續諮詢各一個既有案例）仍 1.00，因為 step 8 的啟動指令改了。
- [x] `claude plugin validate` 通過；harness 的離線 grader 檢查（先例 `check-t11-graders.mjs` 類型的腳本）證明新 regex 對正確回覆通過、對缺欄位的改寫失敗。
- [x] 停止報告行以 grader 證明是模型自己寫在 `TaskStop` 之前的 assistant 訊息（同一行錨定 `"role":"assistant"`），而非只出現在 stop.sh 的 tool_result。
- [x] ticket 08 的 Comments 追加實測可靠度（原本的單次綠燈改記為「三跑二中，於本 ticket 修正後五跑五中」）。
- [x] 每個 grader 改動與 skill 改動都在 plan-verifier READY 的合約範圍內；完成後由 fresh verifier 對「停止路徑離線成立」這個 claim 給 CONFIRMED。

## Comments

**2026-09-18 — implemented; five fix/reverify passes; claim narrowed by the user; resolved.** Skill: step 8 launches through `scripts/run.sh`; the stop path is `stop.sh` → its `Consultation stopped:` line as the first line of the `TaskStop` message → `TaskStop` → `cat -- '<tmp>/stop-report'; rm -rf -- '<tmp>'` (shows the lines the final answer opens with) → final answer; the pre-action `Parallel check:` rule is gone, the parallel state rides on the notice, the question text and the stop line, and step 10 lists one `Parallel check:` line per check plus the stop line and `Failed model:`; step 11 gained the stop-order exception; Failures gained a row for a stopped run; the `TaskOutput` timeout is "the time left in the interval". Graders: `used-run-script`, `used-stop-script`, `stopped-at-stop` (assistant-line-anchored trace regex), rewritten `stopped-line` (full fields, `process tree ended` only — stricter than the spec's "either", deliberate: a `NOT confirmed` in an eval is a defect), `stop-report` judge reworded; parallel: `check-line-before-stop` deleted, `parallel-info-before-stop`, `stopped-report`, `used-*-script` added, `timer-llm` reworded so the fixed line's `still running —` field is not read as "kept waiting". Offline: `ticket-r03-graders.test.mjs` 35/35 (includes the tool-result-only negative trace), `run-stop-scripts.test.mjs` 34/34 on Git Bash and WSL, all other suites green, `claude plugin validate` passes.

**What the rounds found (each fixed offline first).** Round 1 (reachability): the eval sandbox gives every Bash command its own PID namespace (`pid 7 is not running`) → cooperative stop (`stop-request`/`stop-result`, `_tree.sh`). Round 2: `run.sh` sent an empty prompt — a background job's stdin defaults to /dev/null (P1 introduced here; caught by `followup-carries-claims`; fixed with an explicit fd, regression test added); the `TaskOutput` "at most 600000 ms" wording let one run wait the whole 10 minutes; a batch collision (my `TaskStop` did not kill the WSL side — the very defect being fixed) invalidated two runs. Rounds 3–4: the stop line written at the stop but not restated, or restated but not written at the stop; a stderr hint in `stop.sh` moved the stop-moment line to 10/10 but its "then clean up" clause made the model delete both parallel run directories before reading sol's reply (2/5) — removed. Round 5 (structural): `stop-report` file + `cat …; rm -rf …` cleanup line moved the final restatement to 14/15.

**Final bytes, three rounds (15 runs per case).** `timeout-stalled-stop`: launch/stop/cleanup graders 15/15; `stopped-at-stop` **12/15** (4/5, 3/5, 5/5; every miss is a `TaskStop` call in a message with no text at all); `stopped-line` + `stop-report` 14/15 (one answer opened with the line, then a `Read` split it so the last message lacks it); `no-bare-cd` 14/15 (one `cd … && git rev-parse` during root discovery — ticket 17's shape, ticket 06's business). `parallel-shared-timer`: every deterministic grader 15/15 including `parallel-info-before-stop`, `stopped-report`, `check-line`, `Failed model:`; `timer-llm` 10/10 after the rewording (before it, 4/5 with the judge as the only failure on a correct answer). Regression sample 4/4. Eval rounds on the final bytes (2026-09-18): `timeout-stalled-stop` results `2026-09-18T07-35-49-854Z`, `T09-08-55-045Z`, `T09-45-51-402Z`; `parallel-shared-timer` `T07-51-47-845Z`, `T09-25-48-666Z`, `T10-02-44-036Z` (5 runs each); regressions `T07-33-52-914Z` (followup-carries-claims), `T08-11-52-332Z`, `T08-13-58-154Z`, `T08-15-42-756Z`. Kept traces of the third round: `evidence/03-*-trace.jsonl` (10 files).

**Narrowing (user decision).** The 5/5 target for the stop-moment line is not reachable by wording, tool-output hints or structure — the residual is the model acting in a text-less message about one run in five to ten; accepted at the measured rate and recorded in the spec. Known-untested: the `AskUserQuestion` first-line landing (no such tool in the eval). Deferred: the split-final-answer miss and the bare `cd` (ticket 06). Cost of the rounds: about USD 45 across ~90 runs. Lessons recorded in memory: sandbox PID namespaces; background-job stdin; WSL wipes `/tmp` on idle shutdown (two rounds of kept traces were lost, one to that and one to my own copy-then-delete script — the third round's traces are in `evidence/`).

**2026-09-18 — outcome verifier: CONFIRMED on the narrowed claim (six P4 advisories, all DEFER/record).** The verifier re-counted every grader in the six `aggregate-result.json` files, replayed the deterministic regexes on the ten kept traces (counts identical to the aggregates), reran every offline suite (`run-stop-scripts` 34/34, the rest as listed) and `claude plugin validate`, checked the byte-identity premise by mtime and by hashing the grader definitions embedded in the aggregates (only `timer-llm` differs, between round one and two), and read all ten traces for the stop order and the parallel read-before-cleanup. Corrections to the record from its advisories: (1) `stop-report` is also 14/15 in the third round (same split-answer run as `stopped-line`); (2) the `timer-llm` rewording landed *between rounds one and two*, which is why rounds two and three share it; (3) 9 of the 10 traces use the `cat …; rm -rf …` cleanup line — one parallel run cleaned with plain `rm -rf` and opened its answer with "Cleanup complete." before the stop line (`stopped-report` still passes as a contains match); (4) every `TaskStop` in the traces returns `No task found` because `stop.sh` has already ended the tree and `run.sh` has exited — expected under the new order, and `used-taskstop` proves the call, not a kill; (5) rounds one and two of the final bytes are aggregate-only evidence (their traces were lost to WSL's `/tmp` wipe and to my copy-then-delete script); (6) byte identity of SKILL.md/scripts rests on mtimes and the paths in the traces, not on a content hash — the commit hash fixes that from here on.
