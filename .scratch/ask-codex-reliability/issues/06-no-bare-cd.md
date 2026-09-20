# 06 — 諮詢不搬動 shell（ticket 17）

**What to build:** 一次諮詢從頭到尾不改變使用者 shell 的工作目錄。依 01 的 trace 證據找出誘發裸 `cd` 的步驟，只對該步驟補上可照抄的 `env -C` 範例；若 01 的五跑未重現，以「未重現」關票，不改 skill。關閉 ticket 17。

**Blocked by:** 01（需要 trace 證據）。排在 05 之後以共用同一分支，非阻擋。

**Status:** resolved — not reproduced, skill unchanged (2026-09-20)

## Acceptance criteria

- [x] ~~若 01 重現：skill 中誘發 `cd` 的那一步有明確的 `env -C '<dir>' <command>` 範例；`second-opinion-with-stance` `--runs 5` 全過 `no-bare-cd`；同一步驟所在路徑的一個既有案例回歸 1.00。~~ 不適用：01 未重現。
- [x] 若 01 未重現：ticket 17 的 Comments 記錄「五跑未重現、現行 bytes 未觀察到」，Status 改 resolved，skill 不變。
- [ ] 全套中沒有案例在 `no-bare-cd` 上退步（由 07 的全套重跑確認）。
- [x] 改動限於該步驟；Ground rules 的「Never use `cd`」原句不變。

## Comments

**2026-09-20 — 以「未重現」結案。** 依據：01 的 probe E（`second-opinion-with-stance --keep-temp --runs 5` 五跑皆 1.00，五份 trace 共 62 個 Bash 呼叫，任何位置都沒有 `cd`），加上 ticket 04 scenario H 的真實 headless 諮詢（18 個 Bash 呼叫，任何位置都沒有 `cd`）。skill 未改，Ground rules 的「Never use `cd`」原句不變（`SKILL.md:23`）。MVP ticket 17 已 resolved 並記錄同樣內容。未花 eval 費用、未花 Codex 呼叫。第三項驗收（全套中沒有案例在 `no-bare-cd` 上退步）留給 07 的全套重跑確認；若該處出現失敗，ticket 17 連同該次 trace 重新開啟。
