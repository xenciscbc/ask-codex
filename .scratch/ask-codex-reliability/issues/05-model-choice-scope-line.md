# 05 — 模型選擇效力的固定行（ticket 14）

**What to build:** 使用者指定的模型或 effort 與現行設定不同、且無法用 `AskUserQuestion` 詢問時，回覆固定有一行 `Model choice applies to this consultation only: <full model slug>, effort <effort>.`，每次都有；指定的選擇等於現行設定時，這行不出現。關閉 ticket 14。

**Blocked by:** 03（同樣改 step 10 第一項，避免兩張 ticket 同時改同一段；非功能依賴）.

**Status:** needs-triage — reopened 2026-09-21 (Plan R07b S7): the fix holds at about 80-90 %, not 100 %; named exception for the R07b gate, fix after the merge

## 行為改動

- step 0 item 7 的「說出來」改為固定行，指向 step 10。
- step 10 第一項之後自成一行寫出該固定行（純文字，允許 markdown 強調包住固定字，但字、順序與值不可變）。
- 選擇等於現行設定時明文「不寫這行」。

## Acceptance criteria

- [x] `alias-astra` 新增 regex grader（容忍 bold／backtick，要求完整 model slug 與 effort），與既有 `scope-note` llm grader 並列；`--runs 5` 全部 1.00。
- [x] 對照案例（選擇等於現行設定的既有案例，或新增一個最小案例）斷言該行不存在，`--runs 3` 全過。
- [x] 離線證明：regex 對正確回覆通過、對「只寫別名」「缺 effort」「改寫成句子」的改寫失敗。
- [x] ticket 14 resolved，Comments 記錄五跑結果。

## Comments

**2026-09-20 — 完成。** Round 5 on the final bytes (2026-09-20, sonnet, WSL): `alias-astra` 5/5 at 1.00 — `scope-line` (new regex: fixed words, full slug `gpt-6-astra`, `effort medium`) 5/5 and `scope-note` (llm) 5/5; control `override-restated-no-prompt` — `no-scope-line` (new, not_contains) 5/5 and `no-scope-prompt` (llm) 5/5. 對照案例跑了 5 次而非 3 次，因為它在前四輪各有一次失敗。離線證明：`ticket-r05-graders.test.mjs` 14/14。MVP ticket 14 已 resolved，過程與五輪數字記在該票 Comments。

**行為改動比原票多一項**：step 0 item 7 改為有順序的判斷，第二步是一行過程中的工作行 `Model baseline: <slug>, effort <e> (<來源>); named: <slug>, effort <e> — <same|different>.`，分支由 same／different 決定；這一行只屬於過程，step 10 不重述，所以「選擇等於現行設定時回覆沒有多餘說明」仍成立（對照案例的兩個 grader 5/5）。原因：只有固定行時，模型在無法詢問的情況下會直接跳到「只限這次」而略過比對（trace 在 `evidence/05-traces/`）。另外「Model and effort」開頭加了一句先回頭找 session 設定；`scope-note` 的 rubric 補一句「固定行即算說明」（第二輪有一次回覆含該行卻被 judge 3–0 判失敗），判準未放寬。README 兩個語言的「只有三分之一會說」已改為現行行為。

**另行追蹤（不屬本票）**：今天 41 次 run 中 `temp-cleanup` 失敗 2 次（round 3 的 `alias-astra` 一次、round 5 的對照案例一次），沒有留 trace，無法判斷是沒清理還是引號形式不同，也無法歸因於本票（本票未動 step 11，且沒有改動前的同量基線）。已開 ticket 09，交由 07 的全套重跑以 `--keep-temp` 觀察。

費用：五輪約 USD 20.1（3.85＋4.01＋4.85＋2.45＋4.96），Codex 呼叫 0。

**2026-09-21 — reopened by Plan R07b S7: the fix holds at about 80–90 %, not 100 %.** `evidence/07b-s7-run-log.txt` (commit `71ac945`, `SKILL.md` `830c6bd5…`): `override-restated-no-prompt` 8/10 — in both misses the working line reads `Model baseline: gpt-5.6-terra, effort medium (config.toml); named: gpt-6-astra, effort medium — different.` although the history sets astra for the rest of the session: the baseline was taken from `config.toml`, not from the session setting, so the scope line appeared where it must not (`no-scope-line`; the LLM judge `no-scope-prompt` agreed 3:0). `alias-astra` 9/10 — the scope line is written correctly right after the working line, but in the final message it is folded into a sentence ("… — this model choice applies to this consultation only, since it differs from the config-default baseline …") (`scope-line`). The resolution of 2026-09-20 rested on 5/5 + 5/5; a behaviour with a true rate of 0.8 passes 5/5 one time in three. User decision 2026-09-21: named exceptions for the R07b gate (at most 2 and at most 1 misses in 5, those graders only), fix after the merge. What S3 of R07b taught applies here: free wording drifts, fixed wording with an explicit order of work does not — item 7 already fixes the words; what it lacks is where the baseline comes from stated as a lookup BEFORE the comparison, and the restatement as an output slot of step 10 rather than a reminder.
