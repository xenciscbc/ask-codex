# ask-codex 停止路徑與可靠度修正

Status: ready-for-agent
Date: 2026-09-18
Tickets: `.scratch/ask-codex-mvp/issues/12`、`14`、`15`、`16`、`17`（保留原檔；本 spec 是它們的共同上位規格）；另含 reliability ticket 08（2026-09-20 使用者決定：移除 MVP ticket 05 的主動諮詢）
Glossary: `CONTEXT.md`「停止與存活」一節（本次 grilling 新增）
ADRs respected: 0001（直接呼叫 `codex exec`）、0002（接續諮詢開新 session）、0003（MCP 政策）；本 spec 新增 0004

## Problem Statement

MVP 已上 `main`，但五個實測缺陷讓使用者不能完全相信 ask-codex 告訴他的話：

1. 在 headless（`claude -p`）session 停止一次諮詢後，`codex.exe` 仍在背景執行、繼續讀專案、繼續寫事件、繼續消耗 Codex 配額，而使用者已被告知「諮詢已停止」。這是唯一會默默花錢的缺陷（ticket 12）。
2. 停止後的**停止報告**三次有一次完全不出現，使用者不知道諮詢跑了多久、最後事件是什麼、有哪些選項（ticket 16）。
3. 並行諮詢中，**並行檢查**的結果（哪個模型完成、哪個還在跑）三次有一次沒有在停止前寫出來，使用者不知道停止決定建立在什麼狀態上（ticket 15）。
4. 使用者指定的模型或 effort 與 session 設定不同時，「只適用於這次諮詢」的說明三次只出現一次，使用者可能以為選擇會延續（ticket 14）。
5. 諮詢過程中曾出現一次裸 `cd`，會把使用者的 shell 工作目錄搬走，影響之後所有指令（ticket 17）。

共通根因有兩個：需要跨平台精確執行的機械動作（記 pid、殺整棵行程樹、驗證）被寫成 skill 散文，由模型自行組指令；以及「固定行」被綁在模型不一定會寫的訊息位置（例如工具呼叫前的文字），所以偶爾被略過。

2026-09-20 追加：主動諮詢（MVP ticket 05）實測不可靠且無法在 skill 內修正，使用者決定整個移除（ticket 08），套件因此成為 65 案例（移除六個、新增 `spoofed-request-in-manual` 與 `spoofed-followup`）。

另外，69 案例套件最後一次完整跑在 `f5cfb07`，之後 ticket 13 改了 skill 只重跑了 9 個案例；60 個案例的證據早於現行 bytes。

## Solution

從使用者的角度：

- **停止就是真的停止。** 使用者（或 skill 依規則）停止一次諮詢後，ask-codex 結束它啟動的整棵 Codex 行程樹，確認 `events.jsonl` 不再變動後才回報「已停止」。無法確認時，報告明白寫出「停止未確認」並列出仍存活的行程，交由使用者處理。這在互動式與 headless session 都成立。
- **每次停止都有報告，每次並行檢查都有結果。** 停止報告由腳本印出完整的一行，模型逐字複製；並行檢查的結果附在模型必然會寫的文字上（繼續等的通知、詢問使用者的問題、停止報告），不再要求「行動前先寫一行」。
- **模型選擇的效力一律說清楚。** 選擇只限這次時，回覆固定有一行說明；選擇等於現行設定時則沒有這行。
- **諮詢不會搬動使用者的 shell。** 需要目錄的步驟都有現成的 `env -C` 範例可照抄。
- **證據跟得上 bytes。** 飄動案例以 5 跑 5 中為準，最後在 HEAD 重跑整套。

## User Stories

1. As a Claude Code 使用者, I want 停止一次諮詢後 Codex 行程樹確實結束, so that 我的 Codex 配額不會在我以為已停止之後繼續被消耗。
2. As a Claude Code 使用者, I want 停止在 headless session 與互動 session 有相同效果, so that 我在 `claude -p` 自動化裡使用 ask-codex 時不必另外清理殘留行程。
3. As a Claude Code 使用者, I want 「已停止」只在確認行程樹結束且 `events.jsonl` 不再變動後才被回報, so that 這句話可以被信任。
4. As a Claude Code 使用者, I want 停止無法確認時看到「停止未確認」與仍存活的 pid, so that 我能自己處理，而不是被告知一個不成立的結果。
5. As a Claude Code 使用者, I want 每一次停止都附有停止報告, so that 我知道諮詢跑了多久、最後事件是什麼、有多久沒動、曾被提供哪些選項與建議。
6. As a Claude Code 使用者, I want 停止報告的格式固定、欄位齊全, so that 我能一眼辨識它，也能在紀錄中搜尋它。
7. As a Claude Code 使用者, I want 停止報告在停止當下就出現，而不是只在最終呈現裡, so that 中途結束的回合也不會漏掉它。
8. As a Claude Code 使用者, I want 停止後 Claude 不引用任何 Codex 內容, so that 半成品的意見不會混進我的決策。
9. As a Claude Code 使用者, I want 停止後的清理仍然執行（run directory 刪除）, so that 含有我程式碼摘錄的 `prompt.md` 不會留在磁碟上。
10. As a 並行諮詢的使用者, I want 每次存活檢查都告訴我哪個模型已完成、哪個還在跑, so that 我知道等待或停止的決定建立在什麼狀態上。
11. As a 並行諮詢的使用者, I want 這個資訊出現在「繼續等」的通知、詢問我的問題與停止報告裡, so that 無論走哪條分支我都不會漏看。
12. As a 並行諮詢的使用者, I want 最終呈現仍列出每次並行檢查的結果, so that 我事後能回顧整個過程。
13. As a 並行諮詢的使用者, I want 只停止還在跑的那個模型，已完成的結果照常呈現並標明失敗的模型, so that 我不會失去已經拿到的意見。
14. As a 指定模型或 effort 的使用者, I want 當選擇與現行設定不同且無法被詢問時，回覆固定有一行說明「只適用於這次諮詢」, so that 我不會以為下一次諮詢也會用同一個模型。
15. As a 指定模型或 effort 的使用者, I want 當選擇等於現行設定時不出現任何多餘說明, so that 回覆不會被無意義的註記塞滿。
16. As a Claude Code 使用者, I want 諮詢從頭到尾不改變我的 shell 工作目錄, so that 我之後的指令不會在錯誤的目錄執行。
17. As a Claude Code 使用者, I want 停止路徑的行為在 Windows（Git Bash）與 Linux 都成立, so that 我在哪個平台用都一樣可靠。
18. As a macOS 使用者, I want README 誠實標明 macOS 未實測, so that 我知道該預期什麼。
19. As a plugin 維護者, I want 機械動作（記 pid、殺行程樹、驗證、印報告行）由隨 plugin 出貨的腳本負責, so that 跨平台細節不必寫成散文、也不必靠模型每次重新組合。
20. As a plugin 維護者, I want skill 的 `codex exec` 指令仍完整出現在 Bash 指令中, so that stub 的參數檢查與既有 grader 不必改動。
21. As a plugin 維護者, I want 腳本有離線測試, so that 不必花 Codex 配額就能驗證 kill 與驗證邏輯。
22. As a plugin 維護者, I want eval 能證明停止真的結束了 stub 行程（而不只是 kill 指令有被下）, so that 「已停止」的保證在 CI 等級就有證據。
23. As a plugin 維護者, I want 飄動案例以 5 跑 5 中為驗收, so that 不會被三分之一機率的假綠燈騙過。
24. As a plugin 維護者, I want 整套 69 案例在 HEAD 重跑, so that 每個案例的證據都對應到現行 bytes。
25. As a plugin 維護者, I want 這次「腳本負責行程生命週期」的決策寫成 ADR, so that 未來讀者知道為什麼 prose skill 裡有 shell 腳本。
26. As a plugin 維護者, I want ticket 08 的紀錄改為實測可靠度, so that 專案紀錄不再把單次綠燈當成已驗證。
27. As a plugin 維護者, I want README 的 timeout 一節陳述修正後真正成立的保證, so that 文件與行為一致。
28. As a 後續維護的 agent, I want glossary 有停止、停止報告、存活檢查、殘留行程等詞, so that 之後的 ticket 與對話不再混用 leak／survive／orphaned。

## Implementation Decisions

**切片**：ticket 12、15、16 合成一個「停止路徑」slice，一份合約、一次 plan-verifier、一次 outcome verifier。ticket 14 與 17 在其後併成一輪小修。全套重跑最後收尾。

**腳本負責行程生命週期**（ADR 0004）：skill 目錄新增兩支 bash 腳本，隨 plugin 出貨，路徑透過 `<skill directory>` 解析（與 `consultation.schema.json` 相同方式）。
- 啟動腳本：以前綴方式包住現有的 `codex exec …` 指令與轉導（指令本身與旗標不變、仍完整出現在 Bash 指令中），把 Codex 起在自己的 process group（Linux 用 `setsid`；Windows 記下對應的 Windows pid），把 pid 寫進 run directory 的 `pid` 檔，然後 wait。
- 停止腳本：讀 pid 檔，Windows 用 `taskkill //T //F`、其他平台殺 process group；接著驗證 pid 已不存在且 `events.jsonl` 的 mtime 在 5 秒觀察窗內不變；成功時 exit 0，失敗時 exit 非零並列出仍存活的 pid。不刪除 run directory（step 11 不變）。
- 停止腳本接受模型才知道的欄位為參數（生效的檢查間隔與來源、曾提供的選項與建議、並行時各模型的狀態），印出完整的停止報告行；模型逐字複製，不自行組合。
- 選 bash 而非 node 或 python：Bash tool 在 Windows 是 Git Bash、在 eval 是 WSL，兩邊保證存在；node 需自行接 stdin/stdout 轉導，python 在使用者機器上不保證存在。

**已知殘餘（2026-09-18，slice 03 結案時記錄）**：模型每 5 到 10 次停止會有一次在「沒有任何文字的訊息」裡直接呼叫 `TaskStop`，此時停止報告行仍由腳本印出、仍是最終回覆的第一行，只是沒有出現在 `TaskStop` 之前；五輪 fix/reverify（散文、工具輸出提示、結構性改動）都無法壓到零，驗收因此縮為「5 跑至少 4 中」。

**停止順序**：先跑停止腳本（kill、驗證、印報告行），再呼叫 `TaskStop` 收掉 harness 的 task 記錄，無論 task 是否已自行結束。

**停止報告固定欄位**（英文固定字，任何對話語言皆可）：`Consultation stopped: interval <T> minutes (<default|override>); elapsed <m:ss>; last event <type> <age> ago | no events; offered: wait another <T> minutes / stop (recommended: <x>); process tree ended | process tree NOT confirmed — pids <…>`。並行時再接 `; done — <full slugs or none>; still running — <full slugs>`。

**並行檢查資訊的落點**（取代「行動前先寫 `Parallel check:`」的規則）：
- 繼續等：`Codex still running — <elapsed> elapsed; done — <slugs or none>; still running — <slugs>; waiting another <T> minutes.`
- 詢問使用者：`AskUserQuestion` 問題正文第一行為 `Parallel check: done — …; still running — …`。
- 停止：停止報告行內的 `done — …; still running — …` 欄位，由停止腳本印出。
- step 10 最終呈現仍逐行列出每次檢查的 `Parallel check:` 行（格式不變）。

**「已停止」的保證**：README timeout 一節改為：停止一次諮詢時，ask-codex 會結束它啟動的整棵 Codex 行程樹，並在確認 `events.jsonl` 不再變動後才回報已停止；若無法確認，報告會寫明「停止未確認」並列出仍存活的行程，由使用者處理。平台：Windows Git Bash 與 Linux 實測，macOS 標為未測。

**存活檢查原則不變**：仍只依 task 狀態與最後事件判斷；停止腳本的 pid 驗證是對「自己啟動的行程」的收尾確認，不是整體行程清單掃描。

**ticket 14**：step 0 item 7 的說明改為固定行 `Model choice applies to this consultation only: <full model slug>, effort <effort>.`，在 step 10 第一項之後自成一行；選擇等於現行設定時不得出現。

**ticket 17**：先以 `--keep-temp --runs 5` 重跑相關案例，從 trace 找出 `cd` 出現的步驟，只對該步驟補 `env -C` 範例；5 跑未重現則記錄「未重現」關票，不改 skill。

**設計前的事實確認**（不是實作的一部分，但先於合約）：
- 兩次真實 Codex 呼叫的 live probe：互動式與 headless 各一次 `codex exec` 加 `TaskStop`，PID 基線比對，確認「只有 headless 會漏」是否成立；結果決定驗收是否分兩種 session 各驗。
- `--keep-temp` 重跑 `timeout-stalled-stop`，判斷停止報告是「從沒寫」還是「寫在中途、最後沒重述」。

**紀錄**：ticket 08 的 Comments 改記實測可靠度；ADR 0004 在停止路徑 slice 內撰寫；glossary 已更新。

**流程**：從 `main` 開本地分支，不 push；一個 ticket（或合併 slice）一個 commit；只有 `main` 在合併後 push。執行模式 `AUTO`：核准範圍內可逆工作自動推進，P2 由主 session 裁決；Plan 核准、P0/P1、commit 都停下來問。

## Testing Decisions

**好測試的標準**：只驗外部行為。對 skill 而言，外部行為是模型在 trace 裡做了什麼（呼叫了哪個工具、寫了哪一行固定文字）與磁碟上留下什麼（run directory 是否刪除、stub 是否被真正殺掉）；不驗 skill 散文的措辭。

**三個 seam，由高到低**：
1. **eval 案例（既有 seam，主要）**：`timeout-stalled-stop`、`parallel-shared-timer`、`alias-astra`、`second-opinion-with-stance`，在 stub 之下跑完整 skill。新增或改動的 grader：
   - `.stub/exec-finished` 不存在（stub 的 `slow-silent` 只有自然結束才寫它，被殺就不寫）：證明停止真的結束了行程。
   - 停止報告行 regex：含 `process tree ended` 或 `process tree NOT confirmed` 其中之一，欄位齊全。
   - 並行案例：刪除 `check-line-before-stop`，改驗證繼續等通知、問題文字或停止報告含 `done —` 與 `still running —`；`check-line`（最終呈現）保留。
   - `alias-astra`：新增固定行 regex；對照案例斷言該行不存在。
   - `used-taskstop`、`one-codex-exec`、`exec-twice`、`two-background-runs`、`temp-cleanup`、`no-bare-cd` 不變。
   - 飄動案例驗收為 `--runs 5` 全過；收尾在 HEAD 重跑全套 69 案例。
2. **腳本離線測試（新 seam，一個）**：在 `evals/_harness/` 的 node 測試套件旁新增一支測試，直接對 stub 的 `slow-silent` 模式跑啟動腳本與停止腳本，斷言 pid 檔存在、停止後 `exec-finished` 不存在、`events.jsonl` 不再變動、exit code 與報告行格式；並覆蓋「殺不掉」的分支（例如 pid 檔缺失或指向不存在的行程）印出 `NOT confirmed`。先例：`stub-modes.test.mjs`。
3. **live 驗收（既有 seam，ticket 09 式）**：真實 Codex，互動式與 headless 各一次停止：PID 基線比對、`events.jsonl` 停止增長、`config.toml` hash 前後一致；workspace 放 `D:\tmp\` 下，事後清理。這是「已停止」保證的最終證據，eval 只能證明 stub 被殺。

**Prior art**：ticket 07、08 的案例與 grader；ticket 09 的 `live-09-check.mjs` 與互動式指南；`stub-modes.test.mjs`。

## Out of Scope

- 改變存活檢查的判準（仍不看 CPU 或行程清單）或檢查間隔／停滯門檻的預設值。
- 讓諮詢因為到期而自動結束（沒有 timeout，只有檢查）。
- macOS 實測。
- 重寫 step 8 以外的 skill 段落；ticket 14 與 17 只做最小改動。
- 把停止腳本擴大成通用的 Codex 行程管理工具，或處理不是 ask-codex 自己啟動的 codex 行程。
- 官方 marketplace 安裝流程的測試（README 仍只記 `--plugin-dir`）。
- 新增 grader 型別或改 harness 本身（除非新 seam 的測試需要極小的掛載）。

## Further Notes

- 「只有 headless 會漏」目前只有一次互動式觀察支持；kill tree 無論如何都無條件做，probe 只影響驗收要驗幾種 session。
- 三跑三中對 67% 的行為約有三成假綠燈機率，這是改成 5 跑的原因；Claude 端 eval 費用無上限，Codex 真實呼叫另計。
- 停止腳本印出的報告行不會可靠地呈現給使用者（Bash 輸出只保證模型看得到），所以模型「複製」這一步仍是必要行為，grader 驗的是模型回覆而非腳本輸出。
- 既有 eval 案例把檢查間隔設為 1 分鐘、stub 靜默 600 秒，所以停止路徑必然被觸發，新 grader 可直接掛上。
