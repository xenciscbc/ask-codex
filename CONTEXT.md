# ask-codex

ask-codex 是 Claude Code 的 skill，讓 Claude 在工作中途向 Codex 取得意見，並由 Claude 自行判斷是否採納。每個詞彙附上 skill 內容（英文）必須使用的對應用詞。

## Language

**諮詢**（consultation）：
Claude 向 Codex 提出問題並取回意見的一次互動；Codex 只提供看法，決策與任何修改都留在 Claude 端。
_Avoid_: 委派、rescue、把工作交給 Codex 做；英文避免 query、ask、request。

**委派**（delegation）：
把任務本身交給 Codex 執行（可能包含修改檔案），例如官方 codex plugin 的 `/codex:rescue`；不在 ask-codex 的範圍內。
_Avoid_: 將委派與諮詢混用。

### 發起

**手動諮詢**（manual consultation）：
由使用者發起的諮詢，包括輸入 `/ask-codex:ask` 或在對話中明確要求詢問 Codex；發起本身即視為同意。
主動諮詢已於 2026-09-20 移除；所有諮詢皆由使用者發起。

### 模型選擇

**模型簡稱**（model alias）：
使用者對 Codex 模型的簡略稱呼，例如 `sol`、`6 sol`、`astra`；對照 Codex 目前公開列出的模型解析為實際名稱，有歧義時由使用者選擇。
_Avoid_: 固定對照表。

**模型指定**（model override）：
使用者為諮詢指定的模型或 effort；效力是只限這一次還是延續整個 session，由使用者在指定當下選擇。未指定模型時沿用 Codex 設定的模型。

**諮詢 effort**（consultation effort）：
諮詢實際使用的推理強度，永遠不低於 medium；未指定時由 ask-codex 依模型決定，不沿用 Codex 設定中的 effort。
_Avoid_: 讓諮詢以 low 執行。

### MCP 政策

**MCP 政策**（MCP policy）：
決定一次諮詢中 Codex 可使用哪些 MCP server 的規則；Codex 的 shell 指令唯讀，但 MCP server 在 sandbox 外執行，所以另行控制。
_Avoid_: 把 sandbox 唯讀當成涵蓋 MCP。

**白名單模式**（allowlist mode）：
預設的 MCP 政策：除了使用者明確開放的 server 以外全部停用；沒有任何設定時等於全部停用。

**最小停用模式**（minimal-deny mode）：
使用者選用的 MCP 政策：只停用 `node_repl` 與 `cua_repl`，其餘 server 保留。
_Avoid_: A+（討論時的暫稱）。

**ask-codex 設定檔**（ask-codex config）：
記錄 MCP 政策與開放清單的設定，分使用者層與專案層，專案層覆蓋使用者層；由 `/ask-codex:setup` 協助建立。
_Avoid_: 與 Codex 自己的 `config.toml` 混稱。

**專案定義的 server**（project-defined server）：
由專案自己的 Codex 設定新增或改寫的 MCP server；未經使用者在本 session 確認前不得使用。

**MCP 事前檢查**（MCP guard）：
每次送出諮詢前，確認實際生效的 MCP server 與政策預期完全一致的檢查；不一致就中止，不送出。

### 並行諮詢

**並行諮詢**（parallel consultation）：
同時向兩個不同模型提出同一個問題、各自取得獨立意見的手動諮詢；最多兩個模型，不可重複。
_Avoid_: 多模型審查、同一模型重複取樣；英文避免 multi-model review。

**獨立意見**（independent opinion）：
並行諮詢中單一模型的回覆，產生時看不到其他模型的內容。

**共識**（consensus）：
並行諮詢中兩個模型都提出的論點。

**單獨提出**（solo claim）：
並行諮詢中只有一個模型提出的論點。

**分歧**（divergence）：
並行諮詢中兩個模型互相矛盾的論點；Claude 必須說明採納哪一方及理由。

### 討論

**討論**（discussion）：
使用者輸入 `/ask-codex:discuss` 發起、Claude 與單一 Codex 模型針對一個主題（例如功能設計、介面設計）進行多輪的諮詢；只有使用者能發起，一次發起即授權到輪數上限為止的所有輪次。結果是共識、暫定共識以外的爭議點與待使用者決議事項，Codex 仍然不修改任何東西。
_Avoid_: 與並行諮詢的共識／單獨提出／分歧混用；英文避免 debate。

**輪**（round）：
討論中的一次 Codex 呼叫。第一輪雙方各自獨立作答：Claude 先寫下自己的結果，Codex 看不到它；之後每一輪只處理爭議點。

**輪數上限**（round limit）：
一場討論最多進行的輪數，由使用者在發起時選擇；所有討論點都達成共識或交由使用者決議時提前結束。

**討論點**（discussion point）：
討論中的單一主張，標明由 Claude 提出或由 Codex 提出；第一輪之後，只有會改變結論的新討論點才能加入，並另外標示。
_Avoid_: 與諮詢的論點（claim，只指 Codex 的主張）混用。

**暫定共識**（tentative agreement）：
雙方都同意的討論點；之後的輪次作為已鎖定的背景，任何一方只能以本輪某個爭議點的結論影響到它為理由提出重開。討論結束時仍未重開的列為共識。

**爭議點**（contested point）：
尚未達成共識、要帶進下一輪的討論點：Claude 不同意的 Codex 提出點，以及 Codex 尚未表態或不同意的 Claude 提出點。任何一方改變立場時，必須寫出是被哪條論據說服。

**待使用者決議**（user decision item）：
討論結束時交給使用者的討論點：到達輪數上限仍未解決的爭議點，以及雙方都認定取決於使用者偏好或權限、而非技術對錯的討論點（後者一經雙方標示即停止辯論）。每項都附雙方的建議與理由。

### 停止與存活

**檢查間隔**（check interval）：
等待諮詢完成的一段固定時間；到期就做一次存活檢查。未另行指定時為 30 分鐘。
_Avoid_: timeout（諮詢不會因為到期而自動結束）。

**停滯門檻**（staleness threshold）：
最後一個事件距今超過此時間即視為停滯；為檢查間隔的六分之一。

**存活檢查**（liveness check）：
檢查間隔到期時，只依諮詢的 task 狀態與最後一個事件判斷諮詢是否仍在進行；不看 CPU 或行程清單。結果是繼續等、詢問使用者，或停止。

**停止**（stop）：
結束一次仍在進行的諮詢：不採納任何 Codex 內容、結束它的整棵行程樹、清理，並給出停止報告。
_Avoid_: 把「已呼叫停止」當成「已停止」。

**停止報告**（stop report）：
停止後給使用者的說明，必須包含生效的檢查間隔、經過時間、最後事件及其時間、曾提供的選項，以及行程樹是否確認已結束；可依對話語言表達，不要求逐字固定的英文句型。

**殘留行程**（orphaned run）：
停止後仍在執行、仍在消耗配額的 Codex 行程；是缺陷，不是一種狀態。
_Avoid_: leak、survive 等混用說法。

**並行檢查**（parallel check）：
並行諮詢中，一次存活檢查對每個模型的結果：哪些已完成、哪些仍在進行。

### 意見與處置

**附立場**（with-stance）：
Claude 把自己的 Plan、實作或結論連同問題交給 Codex，並明示要 Codex 獨立查證與挑戰；用於第二意見與實作疑點審查。

**盲測**（blind）：
只給 Codex 問題與證據（包括已失敗的嘗試及其結果），不透露 Claude 的結論或假設，以取得未被錨定的觀點；用於診斷與技術問答。
_Avoid_: 把盲測當成隱瞞證據。

**論點**（claim）：
Codex 意見中的單一主張，標明屬於事實或推論、信心程度，並盡可能附證據位置。
_Avoid_: 英文避免 finding、issue（帶有審查缺陷的語意）。

**接續諮詢**（follow-up consultation）：
針對前一次諮詢的後續諮詢，在全新的 Codex session 中進行，附上前一次的論點與 Claude 的處置；範圍鎖定在驗證這些論點，新論點只有達到阻擋等級才可提出並須另外標示。
_Avoid_: 續問、resume 同一個 Codex session；英文避免 resume、continue thread。

**處置**（disposition）：
Claude 對每個論點的判斷：採納（adopt）、不採納（reject）或待查（investigate），並附理由。
_Avoid_: 直接照做 Codex 的建議。

### 諮詢類型

**諮詢類型**（consultation type）：
一次諮詢的用途，由 Claude 依上下文判斷：第二意見、診斷、實作疑點審查、技術問答。
_Avoid_: 讓使用者每次手動指定類型。

**第二意見**（second opinion）：
請 Codex 檢驗並挑戰一份 Plan 或設計決策。

**診斷**（diagnosis）：
卡關時請 Codex 獨立找出 root cause。

**實作疑點審查**（targeted check）：
Claude 帶著具體疑點請 Codex 檢查某段實作或 diff。
_Avoid_: review、code review（整份變更的審查是 `/ask-codex:review`；官方 `/codex:review` 則是逐字回傳 Codex 輸出的原生審查，兩者都不是針對具體疑點的檢查）。

**技術問答**（technical question）：
API 用法、做法比較等不綁定特定修改的一般技術問題。

**審查**（review）：
使用者輸入 `/ask-codex:review` 發起、針對一整份變更（working tree、與 base 比較的 branch，或 commit range）的諮詢；Claude 判斷範圍，Codex 唯讀檢視並回傳論點，Claude 對每個論點給出處置。只有使用者能發起，Claude 不能自行啟動；沒有論點不等於核可。
_Avoid_: 與官方 `/codex:review` 混淆（後者逐字回傳 Codex 輸出、Claude 不加判斷）；英文避免把它稱為 code review 或 approval。
