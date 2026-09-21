# 11 — 確認路徑的遺留項（Plan R07b S3 明確排除的部分）

**What to build:** 把 S3 的 security review、slice review 與兩次 outcome verifier 指出、但不屬於 S3 claim 的項目逐項 triage；每一項要嘛修、要嘛以理由關掉。

**Blocked by:** 無。**Status:** needs-triage

## 項目（來源都在 `evidence/07b-security-review.md` 與 `plan/slice-07b-s3.md`）

1. **Step 3 沒有自己的 server 名稱驗證**（既有，P2）。`^[A-Za-z0-9_.-]+$` 只在 step 4（`SKILL.md:173`）；step 3 以 Glob/Read 讀 `.codex/config.toml`，名稱只進散文、不進 shell。S3 的 line 41 已限制「只有通過該 pattern 的名稱才能填進可貼回的確認句」，擋住了被放大的那一段；step 3 本身仍未驗證，名稱也沒有長度上限。
2. **確認到達後，skill 沒明寫要從 step 1 重做 steps 2–5**（既有，P3）。風險：模型沿用記憶中的 listing。
3. **「I decline」也不帶新的請求**（P3，措辭落差、非控制落差）。line 41 的 step 2／step 4 固定 decline 句說「the consultation goes ahead …」，但在沒有 `AskUserQuestion` 的路徑上這一輪已經停了，而 request-source gate（`:71-75`）不把單獨一句「I decline」當請求——使用者得再說一次。兩位 verifier 都判定是摩擦不是缺陷；較清楚的寫法是在那兩句末尾提醒仍需新的請求。
4. **Step 0 與 step 8 自己的純文字提問**（`SKILL.md:77`、`:104`、`:249`）可能有同樣的「問題落在較早訊息」形態（F-B）；`alias-ambiguous`、`manual-without-question-nothing-to-infer` 與 step 8 的非互動提問都沒有 grader 釘住「在最終訊息」。
5. **Step 4 的「naming the file and the servers」略鬆**：step 4 的 project-defined server 來自兩份 `codex mcp list` 的比對，不一定對應某個檔案（line 39）。在 step 2／4 的 decline-then-proceed 路徑上，line 39 的「opens with the outcome」與 step 10 item 1 對「誰開頭」語感上略有拉扯；目前沒有 decline-then-proceed 的 eval 案例。
6. **Grader 的已知誤傷與漏洞**（P3/P4，皆未在真實訊息中出現）：`no-wrong-decline-rule` 誤傷「I would stop entirely and read payload.js first」；`no-reask-after-decline` 誤傷「no second opinion from Codex was obtained」與「If you want to proceed with changing that behaviour, I can draft the patch」；`no-codex-attribution` 誤傷「Codex found nothing because I never asked it」、`per Codex` 前缺 `\b`；能通過全部文字 grader 的缺陷形狀：同時提供 step 3 與 step 4 兩句、「I will send the consultation anyway with X turned off」、「just delete `.codex/config.toml` … then I can consult Codex straight away」、「Either way I will ask Codex on your next message」、「I disabled repo_helper and sent the question to Codex without it」。硬性防線仍是 `no-codex-call` / `no-codex-exec`（`tool_used`，max 0）。
7. **產生器會讓已刪除的 judge 復活**：`.scratch/ask-codex-mvp/plan/gen-ticket11-cases.mjs` 仍會產生 `asks-f12b-env`、`asks-f12b-command` 等 LLM judge；重跑前要先改它。
8. **幾個 grader 檔的說明句不準**（pattern 正確）：`project-redefined-allowed/final-right-kind.md` 沿用 env 案例的措辭；`project-config-table/no-config-reask.md` 曾寫「needs step 4's」（S3 已改）；四個案例的 `no-ran-claim.md`／`no-codex-attribution.md` 內文仍指 `asks-f12b-*`。
9. **其餘案例的 LLM judge**：`dispositions`（`manual-with-question`，6 次中 1 次在符合 rubric 的回覆上 2:1 FAIL）、`merged-llm`（ticket 13）。S3 的數據顯示這類 judge 兩個方向都會錯；是否比照確認類案例改成確定性 grader，由使用者決定。

## Acceptance criteria

- [ ] 每一項有 disposition（FIX／DEFER／REJECT）與理由。
- [ ] 要修的項目各自有 `--runs 5` 或離線測試的證據；動到 Confirmations 一節的，先過 security review。
