# 13 — parallel 回覆偶爾漏掉 `Divergences` 標題

**What to build:** parallel consultation 的最終回覆每次都帶齊 `Consensus`、`Solo claims`、`Divergences` 三個標題（skill step 10「Parallel reply」：never dropping one because it would be empty），`parallel-two-models` 在 `--runs 5` 全 1.00。

**Blocked by:** 無。**Status:** needs-triage

## Evidence（2026-09-21，Plan R07b S2 的 live 驗收，`SKILL.md` `f0736e96…`）

`parallel-two-models --runs 3`：1.00、0.96、0.96（`temp-cleanup` 三次都過——這不是 S2 的 grader 造成的）。trace 在 `D:\tmp\ask-codex-r07b-traces\s2-parallel-two-models`：

- `claude-eval-JGCUlD`：`h-divergences` 失敗——最終回覆只有 `**Consensus**` 與 `**Solo claims**` 兩個標題，沒有 `Divergences`。fixture 裡兩個 model 對「提高 timeout 能否解決」確實意見相反，所以不是「空的所以省略」，是整段沒寫成獨立標題。
- 另一次：三個標題都在，`merged-llm` judge 2:1 判 FAIL，原因未知（judge 不給理由）。
- 全套單跑（`325afa4`）這個案例是 1.00；三次裡只過一次是新資訊。

## 與 Plan R07b 的關係

step 10 是 R07b 的 non-goal，這個案例不在十個 gate 案例內（覆蓋度：suite only）。若它在 S8 的全套執行低於 1.00，依 R07b 第 2 節的例外規則交給使用者決定，不由 main session 豁免。

## Acceptance criteria

- [ ] `--runs 5` 加 `--keep-temp`，分出「漏標題」與「judge 不穩」各佔多少。
- [ ] 漏標題：step 10 的 Parallel reply 段落修到 `--runs 5` 全過；judge 不穩：`merged-llm` 的可判定部分改成 regex grader 並有離線測試。
