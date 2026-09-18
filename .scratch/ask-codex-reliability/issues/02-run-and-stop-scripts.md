# 02 — 啟動與停止腳本，附離線測試

**What to build:** 隨 plugin 出貨兩支 bash 腳本，接手諮詢行程的生命週期：啟動腳本以前綴方式包住現有的 `codex exec …` 指令，把 Codex 起在自己的 process group、記下 pid、然後 wait；停止腳本殺掉整棵行程樹、驗證已結束、印出完整的停止報告行。不碰 skill 散文；這是讓 03 的改動變容易的 prefactor。

**Blocked by:** None — can start immediately（可與 01 平行）.

**Status:** ready-for-agent

## 行為

- **啟動腳本**：參數為 run directory 與 `--` 之後的完整指令。Linux 用 `setsid` 讓子行程自成 process group；Windows（Git Bash）找出子行程對應的 Windows pid。把 pid（與平台識別）寫進 run directory 的 `pid` 檔，然後 wait 子行程並回傳其 exit code。`codex exec` 指令與轉導由呼叫端寫在同一行，腳本不重組旗標。
- **停止腳本**：參數為 run directory 與模型才知道的報告欄位（生效的檢查間隔與來源、曾提供的選項與建議、並行時各模型狀態）。讀 `pid` 檔，Windows 用 `taskkill //T //F`，其他平台殺 process group；接著驗證 pid 已不存在、且 `events.jsonl` 的 mtime 在 5 秒觀察窗內不變。成功 exit 0 並印出以 `Consultation stopped:` 開頭的完整報告行（欄位見 spec）；失敗 exit 非零，報告行以 `process tree NOT confirmed — pids <…>` 收尾。不刪除 run directory。
- pid 檔缺失或指向不存在的行程時，走「NOT confirmed」分支，不得靜默成功。

## Acceptance criteria

- [ ] 離線測試（放在 harness 既有的 node 測試旁，先例 `stub-modes.test.mjs`）對 stub 的 `slow-silent` 模式跑啟動腳本再跑停止腳本：`pid` 檔存在、停止後 `.stub/exec-finished` 不存在、`events.jsonl` 在觀察窗內不變、exit 0、報告行含 `process tree ended` 與全部欄位。
- [ ] 同一測試覆蓋失敗分支：pid 檔缺失或指向不存在的行程時 exit 非零、報告行含 `process tree NOT confirmed`。
- [ ] 並行欄位：帶 `done`／`still running` 參數時報告行末尾為 `; done — …; still running — …`；不帶時沒有這段。
- [ ] 在 Windows Git Bash 與 WSL Ubuntu 各手動跑一次完整的啟動加停止（對 stub），兩邊都通過；結果記在本 ticket 的 Comments。
- [ ] 腳本只依賴 bash 與各平台內建工具（Windows：`ps -W`、`taskkill`；Linux：`setsid`、`kill`），不需要 node 或 python。
- [ ] harness 既有的所有 node 測試套件仍綠。
