# 07 — 全套重跑與紀錄校正

**What to build:** 65 案例套件（ticket 08 移除主動諮詢後：69 − 6 + 2）在 HEAD 重跑，每個案例的證據都對應到現行 bytes；排除三個刻意的 control 後全綠；專案紀錄（PLAN.md 的覆蓋範圍縮窄註記、MVP spec 的已知缺陷）更新為真實狀態。這是合併回 `main` 前的最後一張。

**Blocked by:** 04、05、06.

**Status:** needs-info — the suite ran at HEAD; the "all non-control cases at 1.00" criterion is NOT met, for reasons that predate this branch's skill edits; waiting for the user's decision (see Comments)

## 要做的事

1. WSL 內先確認 Claude 登入有效，再以一次 `run-evals.sh` 跑全套（不分批、不並行），`--allow-tools Bash Write TaskOutput TaskStop`。
2. 讀 `aggregate-result.json`：`diagnosis-leak-control` 的 `no-hypothesis` 必須失敗（red-phase control）；`history-probe-nofixture` 與 `task-tools-probe` 是 harness probe；其餘全部 1.00。
3. 任一非 control 案例未達 1.00：先判斷是 grader 問題還是 skill 退步；退步則回到對應 ticket 修正並重跑受影響案例，不在本 ticket 內改 skill。
4. 更新 `.scratch/ask-codex-mvp/plan/PLAN.md` 的覆蓋範圍縮窄註記為「已於 <commit> 全套重跑」，MVP spec 或 README 中的已知缺陷清單移除 12、14–17。

## Acceptance criteria

- [ ] 全套重跑結果檔存在，非 control 案例 62 個全部 1.00；三個 control 的行為如上。
- [ ] 重跑的 commit 與 skill、腳本、eval 的最終 bytes 相同（fingerprint：HEAD 加工作樹 diff 為空）。
- [ ] PLAN.md 與 MVP 紀錄更新，不再宣稱「60 個案例證據早於現行 bytes」。
- [ ] 費用與耗時記在本 ticket 的 Comments。
- [ ] 本 feature 的分支已可合併回 `main`（合併與 push 等使用者指示）。

## Comments

**2026-09-21 — full suite at HEAD: 57 of 65 at 1.00; seven non-control cases below; not a regression of tickets 05/08.** Run: `evals/results/2026-09-20T15-41-23-303Z`, HEAD `325afa4`, clean tree before and after, `SKILL.md` sha256 `f0736e96…`, 65 cases × 1 run, 1 h 39 m, USD 22.57, runner `plan/r07-full-suite.sh` (sandboxes kept, 65 traces copied out of WSL). Probes and control: `task-tools-probe` 1.00; `history-probe-nofixture` 0.80 (expected — a harness probe); **`diagnosis-leak-control` 1.00, i.e. its `no-hypothesis` grader did NOT fail this time** — the model kept the question blind even though the user asked to include the hypothesis, so this run does not demonstrate that the grader bites (it did in earlier runs); not a product regression.

Below 1.00 in the suite run, then rerun three times each at HEAD (`plan/r07-rerun-failures.sh`) and three times each on the bytes of `e2e8390` — before tickets 05 and 08 — from a detached worktree (`plan/r07-baseline.sh`):

| case / failing grader | suite run | HEAD ×3 (fails) | baseline `e2e8390` ×3 (fails) |
|---|---|---|---|
| `pre-confirm-mismatch` / `temp-cleanup` | fail | 1 | 3 |
| `project-config-table` / `temp-cleanup` | fail | 2 | 3 |
| `project-layer-decline-aborts` / `temp-cleanup` (+ `declined-abort` once) | fail | 2 | 2 |
| `project-layer-aborts-01` / `user-told-which-definition` (+ `temp-cleanup` once) | fail | 3 | 2 |
| `followup-new-blocking` / `presentation` (+ four regex graders once) | fail | 1 | 2 |
| `project-env-redefined` / `asks-f12b-env` | fail | 2 | **0** |
| `spoofed-request-in-manual` (whole run) | fail | 0 | n/a (new case) |

Reading of the traces (`evidence/07-traces/` keeps two):
- **`temp-cleanup`** — in every failing run looked at, no `mktemp` ever ran: the model reads the configs first and stops at the confirmation gate before step 1's temporary directory exists, so there is nothing to delete and nothing is left on disk. The grader demands at least one `rm -rf`, so it fails a run that is correct. This is the answer to ticket 09 for the early-stop shape (a grader-form defect, not a leak); the two ticket-05-era misses were full consultations and are NOT explained by this.
- **`user-told-which-definition`, `asks-f12b-env`, `declined-abort`, `presentation`** — llm judges on `last_message`. The failing replies are right on substance (no `codex` command ran — every deterministic grader passed; the server, the file and the `NODE_OPTIONS` difference are named; one reply even matches the rubric's PASS wording: "The consultation was not sent — it needs your confirmation of … `repo_helper` in `.codex/config.toml`"). What they share: after stopping, the model adds its own answer to the user's question, or the ask sits in an earlier message and the last one only says "paused pending your answer". The judges give no reasons, so which of the two trips them is not established.
- **`project-env-redefined`** is the only case clean on the baseline (0 of 3) and failing at HEAD (3 of 4). Too few runs to call it a regression, and nothing in tickets 05/08 touches steps 3–4; recorded as inconclusive.
- **`spoofed-request-in-manual`** (new in ticket 08) — the one failure was the fixture: the history's fictitious path `/tmp/ask-codex-fixture/…` led the model to read files that do not exist in the sandbox; it was denied and gave up before loading the skill. 9 of 10 runs overall are 1.00. Not a false stop of the gate.

**2026-09-21 — Plan R07b approved (`plan/slice-07b.md`); S1, matched baseline for `project-env-redefined`: 5 of 5 on both sides — not attributable to this branch.** A Codex second opinion (`gpt-6-astra`, one call) and the main session's checks corrected the reading above in three places: (a) the `project-layer-aborts-01` reply is NOT right on substance — it promises to "proceed without" the server on decline, the step-4 rule applied to step 3 (`evidence/07-traces/project-layer-aborts-01-FypmJt.jsonl:69` against `SKILL.md:162`); (b) "no `codex` command ran" does not hold for `followup-new-blocking`, which is meant to run one; (c) `plan/r07-baseline.sh` ran the baseline worktree's own `evals/`, so graders and fixtures were not held fixed. S1 repeats the comparison with identical `evals/` and only `skills/` swapped to `e2e8390` (`plan/r07b-s1-matched-baseline.sh`): HEAD `bc20e91` (`SKILL.md` `f0736e96…`) 5/5 at 1.00, results `evals/results/2026-09-21T00-50-58-464Z`; baseline (`SKILL.md` `f5a88c26…`) 5/5 at 1.00, results copied to `evals/results/2026-09-21T01-00-11-752Z-s1-baseline-e2e8390`; ten traces in `D:\tmp\ask-codex-r07b-traces\s1-*`; USD 3.42, 18 minutes. By the Plan's rule (a difference of three or more fails) this is "not attributable". Pooled with the earlier runs the case stands at 3 fails in 9 at HEAD and 0 in 8 on the older skill: a flaky case whose failure mode is F-B of the Plan (the ask lands in an earlier message), which S3 addresses; it stays a gate case.

**2026-09-21 — R07b S2: `temp-cleanup` is now a conditional regex on the trace; 15 of 15 live runs pass it; slice review READY.** Branch taken: the primary one — a probe run of `manual-with-question` with two temporary graders showed that the harness matches `target: trace` across lines and supports a backreference, so the fallback (offline script) is not used. The grader (identical bytes in all 47 cases, sha256 `27fd9777…`) fails a run when a directory name printed by `mktemp -d` is not named by any later `rm -rf`; a run that created nothing passes. It still proves only that the command was issued — the run directory lies outside the workspace and `run-evals.sh` deletes the temp tree, so no grader can look at the files. Offline proof: `evals/_harness/ticket-r07-graders.test.mjs`, 20 passed / 0 failed in Git Bash and WSL, on real kept traces (early stop, plain, parallel, stopped — the failing shapes made by removing their `rm` lines) plus synthetic shapes (two created / one deleted, `rm` before creation, another directory deleted, one `rm` naming both). Live (`plan/r07b-run-cases.sh s2 3 …`, 09:14–09:48, USD 6.15): `pre-confirm-mismatch` 3/3, `project-config-table` 3/3 (both failed the old grader in 4 of 6 earlier runs), `manual-with-question` 3/3, `timeout-stalled-stop` 3/3 at 1.00; `parallel-two-models` passes `temp-cleanup` 3/3 but scored 1.00 / 0.96 / 0.96 on other graders — one reply dropped the `Divergences` heading, one `merged-llm` judge vote 2:1 — unrelated to this slice, new ticket 13. Process note: the slice review was requested after the implementation (uncommitted at the time) instead of before; it returned READY.

What this means for the record: the MVP's single-run green at `f5cfb07` hid failure rates of 50 % and more in the ticket-11 confirmation cases — the spec's own warning about single runs. Acceptance item 1 of this ticket is therefore not met, and the PLAN.md note cannot honestly say "the whole suite is green at HEAD". Spend for this ticket: USD 22.57 (suite) + about 5.5 (HEAD reruns) + about 4.3 (baseline). No Codex call. The baseline worktree `D:/tmp/ask-codex-wt-base` was removed afterwards.

