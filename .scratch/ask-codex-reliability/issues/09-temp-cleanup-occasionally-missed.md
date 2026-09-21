# 09 — `temp-cleanup` 偶爾失敗（約 1/20）

**What to build:** 釐清 `temp-cleanup` grader（`rm -rf -- '<含 /ask-codex/ 的單引號路徑>'` 至少一次）在正常完成的諮詢中偶爾失敗的原因：是 run directory 真的沒刪（ticket 13 的缺陷復發，會把含程式碼摘錄的 `prompt.md` 留在磁碟上），還是清理有做、只是指令形式不符 grader（引號、合併指令）。依結果修 skill 或修 grader。

**Blocked by:** 無。**Status:** resolved — on a narrowed statement (2026-09-21, Plan R07b S2 + S7; see the last Comment)

## Evidence（2026-09-20，ticket 05 的五輪 eval）

41 次 run 中 2 次：round 3 `alias-astra` run 2（0.90）、round 5 `override-restated-no-prompt` run 5（0.89），其餘 grader 全過。兩次都沒有 `--keep-temp`，trace 已不存在。ticket 05 沒有改 step 11；沒有「ticket 05 之前」的同量基線，所以無法說是不是新引入的——全套在 `f5cfb07` 是單跑，量不到 5% 的事件。

## 下一步

07 的全套重跑若出現同一失敗，對該案例以 `--keep-temp --runs 5` 重跑並**在同一支 script 內**把 trace 複製出 WSL `/tmp`，讀 trace 後再決定。

## Acceptance criteria

- [ ] 至少一份失敗 run 的 trace，指出是「沒清理」還是「形式不符」。
- [ ] 若是沒清理：skill 修正後相關案例 `--runs 10` 全過 `temp-cleanup`；若是形式不符：grader 放寬到等價形式並有離線測試，且不放過真的沒清理的 run。

## Comments

**2026-09-21 — half an answer from ticket 07's traces.** In the early-stop cases (`pre-confirm-mismatch`, `project-config-table`, `project-layer-decline-aborts`, `project-layer-aborts-01`) `temp-cleanup` fails in roughly half the runs, on today's bytes and on `e2e8390` alike, and every failing trace read shows the same thing: no `mktemp` ran, because the model reads the configs and stops at the confirmation before creating the temporary directory. Nothing is left on disk; the grader's "at least one `rm -rf`" is wrong for that shape. Fix to consider: a grader on the sandbox's files (no `…/ask-codex/run.*` directory left) instead of on the command. The two misses seen during ticket 05 were full consultations (`alias-astra`, `override-restated-no-prompt`), which this does not explain — still open.

**2026-09-21 — closed on a narrowed statement (Plan R07b S2 + S7).** The early-stop half was a grader-form defect, fixed in S2: `temp-cleanup` is now a conditional regex on the trace (every directory `mktemp -d` printed must be named by a later `rm -rf`; a run that created none passes), offline `ticket-r07-graders.test.mjs`. The full-consultation half was NOT reproduced: on the new grader `alias-astra` 10/10 and `override-restated-no-prompt` 10/10 pass `temp-cleanup`, plus `followup-new-blocking` 5/5 (`evidence/07b-s7-run-log.txt`), and every other full consultation run during R07b (S2 15, S3 regression runs, S4 5) passed it too. The two misses of 2026-09-20 stay unexplained — their traces are gone; with the old grader they may have been a form mismatch (one `rm` naming several directories, or `rm -rf` without the single-quoted path form) just as well as a real leak. Not claimed: that a leak cannot happen — the grader proves the command was issued, not that the directory is gone.
