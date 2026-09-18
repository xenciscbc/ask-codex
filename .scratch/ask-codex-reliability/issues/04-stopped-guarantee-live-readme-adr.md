# 04 — 已停止的保證：live 驗收、README、ADR 0004

**What to build:** 使用者讀到 README 的承諾「停止一次諮詢時，ask-codex 會結束它啟動的整棵 Codex 行程樹，並在確認 `events.jsonl` 不再變動後才回報已停止；若無法確認，報告會寫明『停止未確認』並列出仍存活的行程」，而這句話有真實 Codex 的證據支撐。同時把「腳本負責行程生命週期」的決策寫成 ADR，關閉 ticket 12、15、16。

**Blocked by:** 03.

**Status:** ready-for-agent

## 要做的事

1. **Live 驗收**（真實 Codex）：依 01 的結論，在互動式與 headless 各停止一次（若 01 證明只有一種 session 會殘留，仍兩種都驗，但只有會殘留的那種是主要證據）。每次：啟動前 PID 基線、停止後 5 秒與 60 秒 PID 集合、`events.jsonl` 大小在停止後不再增長、停止報告行以 `process tree ended` 收尾。前後取 `config.toml` hash 與 `ask-codex.json` 是否存在。workspace 放 `D:\tmp\` 下，事後刪除。
2. **README（英文與 zh-TW）**：timeout 一節改為 spec 的承諾句；平台註記：Windows Git Bash 與 Linux 實測，macOS 未測；提到 plugin 現在出貨兩支腳本與它們的職責（不列路徑細節）。
3. **ADR 0004**：決策「把諮詢行程的生命週期交給隨 plugin 出貨的 bash 腳本，而非 skill 散文」，含 considered options（散文、node、python）與代價。
4. **關票**：ticket 12、15、16 各追加 Comments（修法、證據、可靠度），Status 改 resolved。

## Acceptance criteria

- [ ] 兩種 session 的 live 證據齊全，停止後 60 秒 PID 集合等於基線、`events.jsonl` 不再增長；證據檔放在本 feature 目錄的 `evidence/` 下。
- [ ] README 兩個語言版本的 timeout 一節與 spec 的承諾句一致；README 內沒有任何一句超出實測範圍（用既有的 `readme-claim-check.mjs` 型式做一次宣稱對照）。
- [ ] ADR 0004 存在，符合 `docs/adr/` 既有格式，三個條件（難逆、無脈絡會奇怪、真實取捨）在文中都能看出。
- [ ] ticket 12、15、16 皆 resolved，Comments 引用 03 的 eval 結果與本 ticket 的 live 證據。
- [ ] `config.toml` hash 前後一致（Codex app 自行改寫的欄位除外，逐一列出）；probe workspace 已刪除。
- [ ] fresh verifier 對「已停止的保證在真實 Codex 上成立」給 CONFIRMED。
