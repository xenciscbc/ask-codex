# 10 — headless session 在諮詢還在跑時結束了 turn

**What to build:** `claude -p` 的諮詢從啟動到呈現都在同一個 turn 內完成；skill step 8 的「Do not end your turn while the consultation is still running」在沒有 `TaskOutput` 阻塞、改用背景計時器等待的路徑上也成立。

**Blocked by:** 無。**Status:** resolved — reproduced and fixed by Plan R07b S6 + S6b, outcome verifier CONFIRMED (2026-09-22; see Comments for what is NOT proven)

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

## Comments

**2026-09-22 — reproduced, cause found, fixed (Plan R07b S6/S6b; contract `plan/slice-07b-s6b.md`; commits `7d58a90`, `0064cf3`, `864fe20`; verifier CONFIRMED).** Reproduction: the eval harness cannot withhold `TaskOutput` — it is a deferred tool the child reaches through ToolSearch whatever `--allow-tools` or the case's `allowed_tools` say (15 of 15 runs called it), and the front-matter key `disallowed_tools` is rejected — so `evals/headless-timer-wait` simulates its absence with `append_system_prompt`. First run on that form: background `sleep 60`, then "Now waiting for either the Codex consultation or the 1-minute timer to complete." — turn over, reply unread, run directory left (`evidence/07b-traces/headless-timer-wait-REzas1-…`). Cause: step 8's fallback told the model to start a background timer and "wait for whichever completion notification arrives first"; a model cannot wait without a blocking tool call, and in a non-interactive session nothing brings it back. `run.sh` left no marker on a normal end, so there was nothing to block on. Fix: `run.sh` writes `<run dir>/exit-code`; new `scripts/wait.sh` blocks in the foreground, file-based, up to 570 s; step 8 (four sentences) waits with it in chunks of at most 540 s and says why; parallel runs name both directories in one wait. Evidence: offline `run-stop-scripts.test.mjs` 65/0 in Git Bash and WSL, `ticket-r10-skill.test.mjs` 50/0; live, final pass at `864fe20`: `headless-timer-wait` 5/5 and the new `headless-timer-stall` 5/5, all ten runs counted (no `TaskOutput` call; traces in `evidence/07b-s6b-traces/`: foreground `wait.sh`, reply read, cleanup issued, C1–C3 and the MCP line / the stop line in the LAST message); regression on the TaskOutput path 11 of 13 with both misses outside the slice (`failed-line` paraphrased → ticket 13; one LLM-judge vote, 3/3 on the rerun). What it took to get counted runs: "the tool is not available" held in 3 of 10 runs — ToolSearch finds the tool and the model believes what it sees; "the tool is broken, calling it ends the session" held in 10 of 10.

**Not proven, follow-ups:** (1) the path when `TaskOutput` is really absent rather than called broken — the runs prove the branch behaves, not that a model takes it; in the main session of 2026-09-21 ToolSearch did not find `TaskOutput` at all, so this may be the only path in current Claude Code; (2) a 30-minute interval needs several consecutive `wait.sh` calls — coherent in the text, never run (every eval uses the 1-minute override); (3) no live headless proof on the real Codex CLI like ticket 04's; (4) design question left open: drop the `TaskOutput` branch and always wait with `wait.sh` — one path, testable without simulation; (5) verifier P4: on Windows a stopped run writes `exit-code=0`, indistinguishable from a normal end, harmless because the stop path does not wait again.
