# 04 — 已停止的保證：live 驗收、README、ADR 0004

**What to build:** 使用者讀到 README 的承諾「停止一次諮詢時，ask-codex 會結束它啟動的整棵 Codex 行程樹，並在確認 `events.jsonl` 不再變動後才回報已停止；若無法確認，報告會寫明『停止未確認』並列出仍存活的行程」，而這句話有真實 Codex 的證據支撐。同時把「腳本負責行程生命週期」的決策寫成 ADR，關閉 ticket 12、15、16。

**Blocked by:** 03.

**Status:** resolved (2026-09-20) — outcome verifier CONFIRMED

## 要做的事

1. **Live 驗收**（真實 Codex）：依 01 的結論，在互動式與 headless 各停止一次（若 01 證明只有一種 session 會殘留，仍兩種都驗，但只有會殘留的那種是主要證據）。每次：啟動前 PID 基線、停止後 5 秒與 60 秒 PID 集合、`events.jsonl` 大小在停止後不再增長、停止報告行以 `process tree ended` 收尾。前後取 `config.toml` hash 與 `ask-codex.json` 是否存在。workspace 放 `D:\tmp\` 下，事後刪除。
2. **README（英文與 zh-TW）**：timeout 一節改為 spec 的承諾句；平台註記：Windows Git Bash 與 Linux 實測，macOS 未測；提到 plugin 現在出貨兩支腳本與它們的職責（不列路徑細節）。
3. **ADR 0004**：決策「把諮詢行程的生命週期交給隨 plugin 出貨的 bash 腳本，而非 skill 散文」，含 considered options（散文、node、python）與代價。
4. **關票**：ticket 12 追加 Comments（live 證據、可靠度），Status 改 resolved；ticket 15、16 已由 03 resolved，本 ticket 只在其 Comments 追加 live 證據的指標。

## Acceptance criteria

- [x] 兩種 session 的 live 證據齊全，停止後 60 秒 PID 集合等於基線、`events.jsonl` 不再增長；證據檔放在本 feature 目錄的 `evidence/` 下。
- [x] README 兩個語言版本的 timeout 一節與 spec 的承諾句一致；README 內沒有任何一句超出實測範圍（用既有的 `readme-claim-check.mjs` 型式做一次宣稱對照）。
- [x] ADR 0004 存在，符合 `docs/adr/` 既有格式，三個條件（難逆、無脈絡會奇怪、真實取捨）在文中都能看出。
- [x] ticket 12 resolved（Comments 引用 03 的 eval 結果與本 ticket 的 live 證據）；ticket 15、16 的 Comments 已補上 live 證據指標。
- [x] `config.toml` hash 前後一致（Codex app 自行改寫的欄位除外，逐一列出——每個 scenario 開始前先備份整個檔案的位元組，且在 Codex app 啟動完成後才取 hash；見 evidence/01 的教訓）；probe workspace 已刪除。
- [x] fresh verifier 對「已停止的保證在真實 Codex 上成立」給 CONFIRMED。

## Comments

**2026-09-20 — done on contract `plan/slice-04.md` (revision 3, READY after two REVISE rounds and a closing review; approved by the user).** Evidence and every number: `.scratch/ask-codex-reliability/evidence/04-live-stop.md`. Codex live calls: **4 of the 5 allowed** — H (pass), I attempt 1 (Codex finished by itself before the second check, checker exit 3), H2 (a headless trial of the user's idea of making Codex `Start-Sleep 240` so the stall is deterministic; Codex's shell tool was down because the desktop app had been closed, and the headless Claude ended its turn early — ticket 10), I attempt 2 with the sleep (pass). Things that went wrong and are written up in the evidence file: a false P1 from the recorder (a dead root's pid reused by an unrelated shell 19 s later; rejected with creation-time evidence, recorder and checker fixed test-first, the recording re-judged unedited); the no-eval-during-live rule was partly broken (an eval job the main session believed it had stopped kept running until 21:42:59; the passing interactive run's Codex started at 21:44:45). README: the promise sentence in both languages (the zh-TW one read from the spec by `plan/readme-claim-check-04.mjs`, which went from 21 failing checks to none), the two scripts, the platform note (Windows live in both session kinds; Linux by offline test and stubbed evals only; macOS untested), the old headless limitation deleted whole, the measured residual added. ADR 0004 written. MVP ticket 12 resolved; 15 and 16 carry the live pointer. `config.toml`: byte-identical across every run; the only change all day was the Codex app's own rewrite when the user reopened it (nine app-owned keys, listed by name). Probe workspace `D:\tmp\ask-codex-live-04` deleted. Seen in passing, not pursued: `codex-computer-use.exe` as a child of `codex.exe` in one interactive run.
