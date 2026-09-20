# 諮詢行程的生命週期交給隨 plugin 出貨的 bash 腳本，而非 skill 散文

ask-codex 是一份散文 skill，但「啟動 Codex、記下它、停止它、確認它真的停了」這段改由兩支隨 plugin 出貨的 bash 腳本負責：`run.sh` 以前綴方式包住完整的 `codex exec …` 指令（指令與旗標仍原樣出現在 Bash 指令中，ADR 0001 不變），把 Codex 起成自己的行程樹並把根 pid 寫進 run directory；`stop.sh` 結束整棵樹（Windows 用 `taskkill /T /F`，其他平台殺 `setsid` 建立的 process group）、確認樹已消失且 `events.jsonl` 在 5 秒內不再變動，然後印出完整的一行停止報告，模型逐字複製。原因是實測：harness 的 `TaskStop` 只收掉 task 紀錄，互動式與 headless session 都一樣，`sh → node → codex.exe` 整條鏈會繼續跑完並花掉整次諮詢的額度，而使用者已被告知「已停止」；把記 pid、跨平台殺行程樹、驗證、組報告寫成散文交給模型每次重組，則出現過停止報告整份缺漏、欄位即興、並行狀態沒寫出來（MVP ticket 12、15、16）。這個決定難以逆轉——README 對使用者的承諾（確認停止後才回報，否則寫明「停止未確認」並列出存活的 pid）、eval 的 grader、以及 `pid`／`stop-request`／`stop-result`／`stop-report` 這組檔案契約都建立在腳本上。沒有脈絡時它也會顯得奇怪：一份散文 skill 帶著 shell 腳本，而且停止同時走兩條路——`stop.sh` 直接殺，並以檔案請 `run.sh` 從自己的行程命名空間內代殺——後者是因為 eval sandbox 裡每個 Bash 呼叫各有自己的 PID namespace，前一個指令記下的 pid 下一個指令看不到，只有 run directory 是共用的。代價：諮詢現在需要 bash（Claude Code 的 Bash tool 在 Windows 是 Git Bash，所以成立，但這是依賴）；macOS 未實測；腳本印出的報告行只保證模型看得到，模型「複製」這一步仍是必要行為，實測約每 5 到 10 次停止有一次，該行只出現在最終回覆開頭而不在停止當下；存活檢查的判準不變，腳本只對自己啟動的行程做收尾確認，不掃描整體行程清單。

## Considered Options

- **維持散文，由模型自行組指令**：不增加任何檔案，但正是實測失敗的做法——`TaskStop` 之後行程鏈存活、停止報告缺漏或即興（MVP ticket 16 三次有一次完全沒有報告）。
- **node 腳本**：Claude Code 的環境一定有 node，但 `codex exec` 的 stdin／stdout／stderr 轉導必須留在呼叫端那一行（stub 的參數檢查與既有 grader 都看那一行），node 包裝得自己接管這些串流；殺行程樹在兩個平台上最後仍是呼叫 `taskkill` 與 `kill`。
- **python 腳本**：使用者機器上不保證存在。
- **bash 腳本（採用）**：Bash tool 在 Windows 是 Git Bash、在 eval 是 WSL，兩邊都保證存在；前綴形式讓原指令與轉導一字不改；離線測試可直接對 stub 驗證殺與驗證邏輯，不花 Codex 額度。
