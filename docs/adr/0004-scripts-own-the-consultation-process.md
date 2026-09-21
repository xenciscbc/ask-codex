# 諮詢行程的生命週期交給隨 plugin 出貨的 bash 腳本，而非 skill 散文

ask-codex 是一份散文 skill，但「啟動 Codex、記下它、停止它、確認它真的停了」這段改由兩支隨 plugin 出貨的 bash 腳本負責：`run.sh` 以前綴方式包住完整的 `codex exec …` 指令（指令與旗標仍原樣出現在 Bash 指令中，ADR 0001 不變），把 Codex 起成自己的行程樹並把根 pid 寫進 run directory；`stop.sh` 結束整棵樹（Windows 用 `taskkill /T /F`，其他平台殺 `setsid` 建立的 process group）、確認樹已消失且 `events.jsonl` 在 5 秒內不再變動，然後印出完整的一行停止報告，模型逐字複製。原因是實測：harness 的 `TaskStop` 只收掉 task 紀錄，互動式與 headless session 都一樣，`sh → node → codex.exe` 整條鏈會繼續跑完並花掉整次諮詢的額度，而使用者已被告知「已停止」；把記 pid、跨平台殺行程樹、驗證、組報告寫成散文交給模型每次重組，則出現過停止報告整份缺漏、欄位即興、並行狀態沒寫出來（MVP ticket 12、15、16）。這個決定難以逆轉——README 對使用者的承諾（確認停止後才回報，否則寫明「停止未確認」並列出存活的 pid）、eval 的 grader、以及 `pid`／`stop-request`／`stop-result`／`stop-report` 這組檔案契約都建立在腳本上。沒有脈絡時它也會顯得奇怪：一份散文 skill 帶著 shell 腳本，而且停止同時走兩條路——`stop.sh` 直接殺，並以檔案請 `run.sh` 從自己的行程命名空間內代殺——後者是因為 eval sandbox 裡每個 Bash 呼叫各有自己的 PID namespace，前一個指令記下的 pid 下一個指令看不到，只有 run directory 是共用的。代價：諮詢現在需要 bash（Claude Code 的 Bash tool 在 Windows 是 Git Bash，所以成立，但這是依賴）；macOS 未實測；腳本印出的報告行只保證模型看得到，模型「複製」這一步仍是必要行為，實測約每 5 到 10 次停止有一次，該行只出現在最終回覆開頭而不在停止當下；存活檢查的判準不變，腳本只對自己啟動的行程做收尾確認，不掃描整體行程清單。

## Considered Options

- **維持散文，由模型自行組指令**：不增加任何檔案，但正是實測失敗的做法——`TaskStop` 之後行程鏈存活、停止報告缺漏或即興（MVP ticket 16 三次有一次完全沒有報告）。
- **node 腳本**：Claude Code 的環境一定有 node，但 `codex exec` 的 stdin／stdout／stderr 轉導必須留在呼叫端那一行（stub 的參數檢查與既有 grader 都看那一行），node 包裝得自己接管這些串流；殺行程樹在兩個平台上最後仍是呼叫 `taskkill` 與 `kill`。
- **python 腳本**：使用者機器上不保證存在。
- **bash 腳本（採用）**：Bash tool 在 Windows 是 Git Bash、在 eval 是 WSL，兩邊都保證存在；前綴形式讓原指令與轉導一字不改；離線測試可直接對 stub 驗證殺與驗證邏輯，不花 Codex 額度。

## 2026-09-22 增補：等待也交給腳本（`wait.sh`，reliability ticket 10）

原本的 step 8 在沒有 `TaskOutput` 時要模型「啟動背景計時器，等先到的完成通知」。模型沒有辦法「等」——它一停止呼叫工具，turn 就結束；互動 session 會被完成通知叫回來，headless（`claude -p`）不會，於是 Codex 跑完沒人讀、結果沒呈現、含程式碼摘錄的 `prompt.md` 留在磁碟上（ticket 10，以 eval 案例 `headless-timer-wait` 重現）。現行的 Claude Code session 可能根本沒有 `TaskOutput`，所以這條「備援」可能就是唯一的路徑。修法沿用本 ADR 的決定：`run.sh` 在被啟動的指令結束時把 exit status 原子寫入 `<run dir>/exit-code`（stop 之後也寫），新增的 `wait.sh` 在前景阻塞到每個指名的 run directory 都有 `exit-code` 或時間到，一律以檔案判斷——eval sandbox 裡每個 Bash 呼叫各有自己的 PID namespace，pid 跨呼叫沒有意義。檔案契約因此多一個 `exit-code`。代價與界線：Bash tool 的前景指令上限是 10 分鐘，所以預設 30 分鐘的間隔要連續呼叫數次（每段至多 540 秒）——這條多段路徑只有文字自洽與離線測試，eval 都用 1 分鐘的 override；`run.sh` 自己被殺或在啟動前因用法錯誤退出時不會有 `exit-code`，`wait.sh` 只會回報 `still-running`，由 step 8 的存活檢查在一個間隔後導向 stop path（有界）；Windows 上被 stop 的執行會寫出 `exit-code=0`，與正常結束無法區分，但 stop path 之後不會再等待。未決定的事：是否乾脆拿掉 `TaskOutput` 分支、一律用 `wait.sh`（只剩一條路徑，不必模擬就能測）——留給 ticket 10 的後續。
