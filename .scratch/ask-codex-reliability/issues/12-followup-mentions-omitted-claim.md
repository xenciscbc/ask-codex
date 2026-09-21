# 12 — follow-up 回覆提到「已省略」的 claim

**What to build:** follow-up 的最終回覆對「非 new-blocking 的新 claim」完全不提——不呈現、也不說它被省略（`SKILL.md` step 10「Follow-up reply」：omitted — not presented, and not mentioned at all (not even to say that it was omitted)）。`followup-new-blocking` `--runs 5` 全 1.00。

**Blocked by:** 無。**Status:** needs-triage

## Evidence（2026-09-21，Plan R07b S7，`SKILL.md` `830c6bd5…`，`evidence/07b-s7-run-log.txt`）

`followup-new-blocking --runs 5`：run 1 的最終回覆寫「(C5, a non-blocking naming suggestion, is omitted per the follow-up rules.)」→ `c5-not-mentioned` 失敗。5 次中 1 次；ticket 07 的 9/20 全套與三次重跑也各見過一次同形態。trace：`D:\tmp\ask-codex-r07b-traces\s7-followup-new-blocking\`。

同一輪另有 2 次是 LLM judge `presentation` 3:0 判 FAIL，但那兩則回覆逐條符合 rubric（C2 標 unresolved 並有 updated disposition、C4 在「New blocking claim from Codex」標題下獨立列出並有 disposition、沒有 C5）——judge 誤判；依 Plan R07b S7(ii)，該 judge 已由確定性 grader 取代（`c4-under-heading` 加上既有的 `c2-unresolved`、`c2-updated`、`heading`、`c4-shown`、`c5-not-mentioned`、`c5-omitted`）。

## 與 Plan R07b 的關係

step 10 是 R07b 的 non-goal。使用者 2026-09-21 決定：列為具名例外（gate 5 跑至多 1 次、僅限 `c5-not-mentioned`），merge 後再修。

## Acceptance criteria

- [ ] step 10 的 Follow-up reply 段落修到 `followup-new-blocking` `--runs 5` 全 1.00（S3 的經驗：自由措辭會飄、固定措辭不會；「不要提」這類否定規則可能需要改寫成正面的輸出清單）。
