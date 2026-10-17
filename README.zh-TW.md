# ask-codex

*[English version](./README.md)*

ask-codex 是一組 Claude Code skills，也提供 plugin 安裝方式，透過本機 OpenAI Codex CLI 取得獨立意見。Claude 準備問題、判斷回覆，並對每個實質論點給出**採納、不採納或待查**的處置及理由。實作決策仍由你與 Claude 負責。

## 目前能力

- 五種諮詢類型：第二意見、診斷、實作疑點審查、技術問答與接續諮詢。診斷與技術問答不透露假設，降低答案被錨定的機會。
- 支援模型簡稱與明確的 reasoning effort；最多兩個不同模型各自回答。接續諮詢會開啟新 session，攜帶前次論點與處置。
- 腳本負責設定解析、MCP 授權檢查、執行、有時間上限的等待、行程追蹤與結構化結果。
- 安全傳遞 Unicode 回覆；輸出失敗可重新收集結果，並分開回報交付與清理失敗。
- 整體變更審查：`/ask-codex:review` 把 working tree、與某個 base 比較的 branch，或一段 commit range 交給 Codex 審查，由 Claude 判斷每個論點。只有你輸入指令才能啟動。
- 多輪討論：`/ask-codex:discuss` 讓 Claude 與一個 Codex 模型針對一個設計主題進行多輪討論——先各自獨立作答，之後只討論有爭議的部分——最後回報雙方的共識，以及需要你決定的事項與雙方各自的建議。只有你輸入指令才能啟動。
- UI 演練：`/ask-codex:ui` 讓 Codex 在隔離、網路受限的 Chrome 中實際操作你的 web app——在專案的可丟棄副本上，或在你要求時直接用你已在執行的 dev server——並回報 bug、版面問題與 UX 建議；Claude 透過同一個受限瀏覽器重現每個 bug 論點，並判斷每個論點。只有你輸入指令才能啟動。僅限 Windows。見 [UI 演練](#ui-演練ask-codexui)。
- 諮詢、審查與討論的目前實作目標為 Windows 搭配 Git Bash，以及 Linux；UI 演練僅限 Windows。兩者皆有離線測試；真實 Claude 的驗證目前僅涵蓋 WSL 上兩個搭配 stub Codex 的 headless 案例。此版完整的真實 Codex 諮詢與互動流程尚未驗證。

## 執行邊界

諮詢以 Codex 的唯讀 shell sandbox 執行，並關閉子代理（自 1.3.2 起帶 `-c agents.enabled=false -c features.multi_agent_v2.enabled=false`，見下方已知風險「子代理」）、拒絕任何跳出 sandbox 的提升權限（自 1.3.3 起帶 `-c approval_policy="never" -c approvals_reviewer="user"`，見「提升權限核准」），且不載入 execpolicy `.rules` 檔（自 1.3.3 起帶 `--ignore-rules`）。shell sandbox 會擋寫入與對外網路；在 Windows 上不擋 loopback，所以 shell 指令連得到這台機器上所有 localhost 服務（見「本機服務」）。MCP server 在該 sandbox 之外執行；腳本預設停用事前檢查時觀察到的所有 server。檢查與執行之間的設定變更可能繞過檢查，詳見下方限制。你允許的 server 可能提供寫入或執行工具；外掛不會讓這些工具變成唯讀。

UI 演練是另一種互動，有自己的邊界（[ADR 0009](docs/adr/0009-exercise-on-a-disposable-target.md)）：同樣的唯讀 shell 與指令列固定值；除了一個固定版本、受限制的瀏覽器 MCP server 之外，所有 MCP server 都停用，該 server 列出的工具逐一預先核准；以及一個結束後會移除的可丟棄目標。Codex 與它的瀏覽器不會寫入你的專案。這個邊界涵蓋與不涵蓋什麼，見 [UI 演練](#ui-演練ask-codexui)。

Skill 要求 Claude 只在你提出要求時諮詢，並將 Codex 輸出視為資料。這是模型指示，並非 hook 或工具層的授權屏障。行程停止也依賴可觀測的行程身份與快照，限制詳見下文。

## 安裝與更新

可選擇 marketplace plugin 或手動複製 skills；兩者都需要下方列出的先決條件。

### 方式一：從 GitHub 安裝 plugin

在 Claude Code 中加入此儲存庫的 marketplace，再安裝外掛：

```text
/plugin marketplace add xenciscbc/ask-codex
/plugin install ask-codex@ask-codex
```

第一個 `ask-codex` 是外掛名稱，第二個是此儲存庫定義的 marketplace 名稱。安裝後使用 `/ask-codex:ask`、`/ask-codex:review`、`/ask-codex:discuss`、`/ask-codex:ui` 與 `/ask-codex:setup`。

也可以在終端機安裝至使用者範圍：

```bash
claude plugin marketplace add xenciscbc/ask-codex
claude plugin install ask-codex@ask-codex --scope user
```

更新這份安裝：

```bash
claude plugin marketplace update ask-codex
claude plugin update ask-codex@ask-codex --scope user
```

若當初安裝於 `project` 或 `local` 範圍，請改用對應 scope。安裝或更新後重新啟動 Claude Code，也可在進行中的 session 使用 `/reload-plugins`。自動更新可於 `/plugin` → **Marketplaces** → **ask-codex** → **Enable auto-update** 開啟；第三方 marketplace 預設不會開啟。參考官方[安裝指南](https://code.claude.com/docs/en/discover-plugins)與[外掛 CLI 文件](https://code.claude.com/docs/en/plugins-reference)。

維護者發布外掛更新時，必須提高 `.claude-plugin/plugin.json` 的 `version`。只新增 Git tag，不會改變已安裝外掛的版本判定。詳見[版本管理](https://code.claude.com/docs/en/plugin-marketplaces#version-resolution-and-release-channels)。

### 方式二：手動複製 skills

下載或 clone 此儲存庫，將下列**完整目錄**複製到選定範圍：

| 來源 | 個人安裝 | 僅限專案 |
|---|---|---|
| `skills/ask/` | `~/.claude/skills/ask/` | `<project>/.claude/skills/ask/` |
| `skills/review/` | `~/.claude/skills/review/` | `<project>/.claude/skills/review/` |
| `skills/discuss/` | `~/.claude/skills/discuss/` | `<project>/.claude/skills/discuss/` |
| `skills/setup/` | `~/.claude/skills/setup/` | `<project>/.claude/skills/setup/` |
| `skills/ui/` | `~/.claude/skills/ui/` | `<project>/.claude/skills/ui/` |

Windows 的 `~` 是使用者家目錄，通常為 `C:\Users\<username>`。`ask` 必須包含 `SKILL.md`、`prompts/`、`scripts/`、`consultation.schema.json`、`discussion.schema.json`、`ui-exercise.schema.json`、`browser-server/` 與 `guard-page/`，不能只複製 `SKILL.md`。`setup` 提供 MCP 政策設定輔助功能，也負責為 UI 演練準備機器。`review`、`discuss` 與 `ui` 透過 `ask` skill 的腳本與 prompt 執行，並以相鄰目錄（`../ask`）找到它們，因此只能與 `ask` 一起複製到同一個上層目錄。

使用上述目錄名稱時，指令是 `/ask`、`/review`、`/discuss`、`/ui` 與 `/setup`，取代本 README 其他段落中的 plugin 前綴指令。也可以直接用自然語言明確要求 Claude 諮詢 Codex。參考 Claude Code 的[skill 位置與命名規則](https://code.claude.com/docs/en/skills)。

更新時，下載或 pull 最新儲存庫，以相應的新目錄替換已安裝的目錄，包含所有支援檔案；若有自行修改，請先備份。手動複製的 skills 不由 `claude plugin update` 管理。

### 本機開發與 headless 執行

不安裝外掛、直接測試本機 checkout：

```bash
claude --plugin-dir /path/to/ask-codex
```

使用該 checkout 執行 headless 諮詢：

```bash
claude -p --plugin-dir /path/to/ask-codex \
  --permission-mode acceptEdits \
  --allowedTools Bash Read Glob Grep Skill Write TaskOutput TaskStop \
  "/ask-codex:ask Why does fetchUser return an empty object on timeout?"
```

已安裝的 plugin 不需要 `--plugin-dir`；headless 執行仍須取得必要工具權限。已記錄的真實 Claude 檢查使用 WSL 本機載入與 stub Codex；此專案的驗證尚未對 marketplace 安裝／更新或手動複製 skills 執行端對端測試。

## 先決條件

- 支援 skills 或 plugin 的 Claude Code，並允許使用所需的檔案與 Bash 工具。
- Python 3.11 以上版本。諮詢腳本使用標準函式庫的 `tomllib` 讀取 Codex 設定。
- Bash。Linux 直接使用 Bash；Windows 必須使用 Git Bash。
- 已安裝並登入的 Codex CLI。未登入時 Claude 會告訴你執行 `! codex login`。
- 僅 `/ask-codex:ui` 需要：Windows、Google Chrome（stable channel）149 以上，以及 `PATH` 上附帶 npm 的 Node.js。先執行一次 `/ask-codex:setup` 並要求它為演練做準備：它會安裝固定版本的瀏覽器 server 並檢查這些相依項目（見 [UI 演練](#ui-演練ask-codexui)）。演練以 `codex-cli 0.159.3` 測試。
- 舊版實作曾以 `codex-cli 0.154.0` 驗證。當時測試機器上的 `codex` 解析到 pnpm 安裝的 `@openai/codex`，而非 Codex 桌面應用自帶的執行檔——兩者都安裝時，實際使用的是 `PATH` 上的那一個。

## 使用方式

```text
/ask-codex:ask 為什麼 fetchUser 逾時時會回傳空物件？
/ask-codex:ask sol:high 檢查這份 diff 的重試邏輯。
/ask-codex:ask astra, sol 對這份計畫提供第二意見。
/ask-codex:review
/ask-codex:review --base main
/ask-codex:review sol main..HEAD 檢查錯誤處理
/ask-codex:discuss 登入服務應該如何限制密碼猜測？
/ask-codex:discuss sol:high rounds 5 設計外掛的設定檔格式。
/ask-codex:ui
/ask-codex:ui sol:high --headed 結帳流程
/ask-codex:setup
```

簡稱會對照本機 Codex 模型清單解析；範例不代表你的帳號一定可使用這些模型。

**手動諮詢。** 輸入 `/ask-codex:ask`（可附問題，也可不附），或直接用自己的話說「問一下 Codex」「聽聽 Codex 的看法」。提出要求本身即視為同意。沒有附問題時，Claude 會從對話推論出問題，並在送出前以一行揭示。Skill 要求每次諮詢都必須來自你的要求；實際約束範圍如上所述。

**諮詢類型。** Claude 依上下文判斷：第二意見（檢驗並挑戰一份 Plan 或決策）、診斷（卡關時找出 root cause）、實作疑點審查（帶著具體疑點檢查某段實作或 diff）、技術問答，以及接續諮詢。診斷與技術問答採**盲測**送出——不透露 Claude 自己的假設，以免答案被錨定。

**模型與 effort。** 可用**模型簡稱**指定（`sol`、`astra`、`6 sol`），或連同 effort 一起指定（`sol:high`）；簡稱有歧義時 Claude 會列出候選並詢問。未指定模型時，Claude 會先用本 session 先前選定的模型，其次是 Codex 設定中的 `model`，再其次是本機快取中可見且優先序最高的模型；這些來源都沒有模型時，交由 CLI 使用預設值。**諮詢 effort** 永遠不低於 `medium` 且一律明確傳入，不會沿用 Codex 設定裡的 effort；`ultra` 需要使用者明確要求且模型支援。當你的**模型指定**與目前設定不同時，互動 session 會問這次指定只限這一次，還是延續本 session 其餘；headless 執行無法詢問，因此只套用於該次諮詢，並以對話語言在報告中揭露適用範圍，不要求固定句子或行位置。模型與 effort 和本 session 現行設定相同時，不需另加範圍說明。

**審查。**`/ask-codex:review [model tokens] [--base <ref> | A..B | A...B] [focus]` 針對一份完整變更諮詢 Codex。預設範圍是 working tree（staged、unstaged 與 untracked 檔案）；`--base <b>` 指 `HEAD` 上自與 `<b>` 的 merge base 以來的 commits（只含已 commit 的變更，不含未 commit 的修改）；`A..B` 與 `A...B` 指定明確的 commit range。其餘文字是你的 focus，原樣交給 Codex。模型 token 的用法與 `ask` 相同，也可並行兩個模型。Claude 以強化過的唯讀 git 指令解析每個 ref（形似選項的 ref 會被拒絕；範圍為空或被拒絕時不會執行任何東西），把範圍與這份變更的意圖（作為立場）交給 Codex，由 Codex 自行唯讀檢視 diff。報告以範圍行開頭，接著列出每個論點與 Claude 的處置；沒有任何論點不代表通過審查。**審查僅限使用者啟動：**skill 停用了模型呼叫，Claude 無法啟動它，只有輸入該指令才會執行；自然語言的審查請求不會被轉成審查。若要求對整份變更做審查，`ask` 會告知有這個指令，而不是自行執行。Claude 絕不因為某個論點而修改任何東西。

**討論。**`/ask-codex:discuss [model token] [rounds <n>] [topic]` 讓 Claude 與一個 Codex 模型針對一個主題（功能設計、介面設計、工作流程）進行多輪討論。第一輪雙方各自獨立作答：Claude 在 Codex 啟動前先寫下自己的結果，Codex 看不到它。接著 Claude 整合兩份結果：雙方都提出的點成為**暫定共識**，Claude 同意的 Codex 論點也併入其中，其餘——Claude 不同意的 Codex 論點，以及 Claude 自己提出的點——成為**爭議點**。之後每一輪只把爭議點連同雙方完整的理由與證據，送到**全新的** Codex session（不 resume，理由見 [ADR 0007](docs/adr/0007-discuss-skill.md)）；Codex 對每一點表示接受、維持或修正，Claude 再逐一回應。所有點都不再有爭議，或到達輪數上限時結束：輪數可在指令中用 `rounds <n>`（2–10）指定，否則 Claude 會詢問（3、5、7 或自行輸入），headless 執行則使用 3 輪並在報告中說明。報告分三部分：過程（每輪一兩行，誰被哪條論據說服）、共識（包含雙方都同意放棄的點），以及**待你決定**的事項——到最後仍有分歧的點，以及雙方都認為屬於你的偏好或權限的點——每項都附 Claude 與 Codex 各自的建議與理由。為了避免假性共識：讓步必須引用具體證據，否則標為「無證據讓步」；第 3 輪以後才翻轉的點會特別標示；第一輪之後只有會改變結論的新論點才能提出；這些規則對 Claude 與 Codex 一體適用。某一輪失敗、被停止或回覆不符格式時，討論就此結束並給出部分報告，不會重試。每場討論只有一個模型參與，且全程固定。**討論僅限使用者啟動**，與審查相同：Claude 無法自行啟動，以自然語言提出要求時，`ask` 會告知有這個指令。Codex 只讀取，套用與 `ask` 相同的 MCP 政策，且每一輪開始前都會檢查；主題需要外部文件時，可依下方 MCP 政策段落開放文件類 MCP server。

**並行諮詢。** 指定兩個不同模型（`astra, sol`）可讓兩者回答同一個問題並各自給出**獨立意見**，再合併為**共識**、**單獨提出**與**分歧**三類，每個論點標註來源模型，每個分歧都說明採納哪一方及理由。最多兩個模型，且不可重複。

**接續諮詢。** 接續諮詢在全新的 Codex session 進行，附上前一次的論點與 Claude 的處置，並要求 Codex 逐項回報狀態；不會 resume 先前的 Codex session。

**腳本主導執行與長時間執行。** Claude 準備問題並判斷答案；[`skills/ask/scripts/consult.py`](skills/ask/scripts/consult.py) 負責政策解析、事前檢查、安全組合指令、行程生命週期與結構化狀態。啟動前，它會提供可檢視的摘要，列出模型與 effort、專案目錄、允許的 MCP server 與生效政策。狀態會區分待確認、事前檢查失敗、執行中、完成、執行失敗、已確認停止與停止未確認；執行錯誤不會被當成 Codex 意見。

Claude 預設每 30 分鐘檢查一次進行中的諮詢；每段前景等待最多 60 秒，也不會超過該次檢查區間的剩餘時間。看起來停滯時，互動 session 會顯示已經過時間與最後事件，詢問要再等一輪還是停止；headless 執行會回報相同資訊並依既有停止路徑處理。腳本的行程身份與行程樹檢查通過後，才會回報停止已確認；此判斷仍受下文的快照限制影響。停止若無法確認，控制檔與診斷資料會保留，包含仍存活行程可能正在使用的檔案，並回報其位置。這些診斷資料沒有自動到期機制，只會在使用者明確要求清理後移除；log 仍可能含有專案內容。行程確認結束後，prompt 與 reply 會移除，不作為長期診斷資料保留。

**回覆交付與恢復。** 收集結果時，腳本先以 ASCII-safe JSON 完整輸出並 flush 回覆，再刪除成功執行的檔案，因此即使 Windows 使用舊式輸出編碼，也能保留 Unicode 內容。輸出失敗時檔案會保留，Claude 可以重新收集同一份結果，不必重新諮詢。回覆交付後若清理失敗，會分別回報有效回覆與保留位置。模型啟動後不會自動重試諮詢。

**MCP 政策。** 腳本預設停用事前檢查時觀察到的所有 MCP server（**白名單模式**、空清單），仍受下方設定競態限制影響。你可以開放特定 server，或改用**最小停用模式**，只停用 `node_repl` 與 `cua_repl`。設定記錄在使用者層與專案層的 **ask-codex 設定檔**，專案層覆蓋使用者層；`/ask-codex:setup` 會協助建立。政策檔不存在時採用文件記載的 fallback；既有政策檔若有無效 JSON、型別、政策值或 server 名稱，會在 Codex 啟動前採 fail-closed 中止。腳本在執行前檢查實際生效的 MCP 狀態，並把含點號的 server 名稱視為完整名稱處理。

政策檔逐欄位合併：

| 範圍 | 檔案 |
|---|---|
| 使用者 | `~/.claude/ask-codex.json` |
| 專案 | `<project>/.claude/ask-codex.local.json` |

server 名稱就是 Codex 自己使用的名稱：執行 `codex mcp list` 可以看到，`/ask-codex:setup` 也會列出來。例如，下列政策只允許名為 `docs`、且已在 Codex 啟用的 server：

```json
{"mcp_policy": "allowlist", "mcp_allow": ["docs"]}
```

Setup skill 只寫入 ask-codex 政策檔，不會修改 Codex 的 `config.toml`。專案本機政策應排除於版本控制之外。準備階段可能要求對專案政策或 server 使用權限進行 session 確認；headless 若仍有待確認事項，就不會執行諮詢。

專案定義的 server 必須取得明確的來源確認，而且確認綁定該次定義內容；command、argument、endpoint、environment 或其他定義欄位一旦改變，先前確認即失效。來源確認只表示認可該定義，允許使用 server 是另一個決定；Claude 可以在同一個問題中清楚分別詢問兩者。確認 ID 由準備完成的定義產生，本身不能構成同意。

## UI 演練（`/ask-codex:ui`）

`/ask-codex:ui [model token] [--headed] [scope or focus]` 讓 Codex 實際使用你的 web app，而不是閱讀它的程式碼。Codex 在隔離的 Chrome 中操作 app——瀏覽頁面、點擊、填表、調整成包含手機尺寸在內的多種 viewport、截圖並實際看圖、讀取瀏覽器 console 與網路紀錄——並回傳論點：bug、版面問題與 UX 建議。範圍內的每個 bug 論點，Claude 都會先透過同一個受限瀏覽器自行重現，才標為已確認（否則回報為未確認，並列出嘗試過的步驟）；每個版面與 UX 論點都給出處置與理由，然後回報。不會修正任何東西。**演練僅限使用者啟動：**只有輸入指令才會開始，而且要等你回覆確認訊息後才會啟動；確認訊息會列出每個指令、位址、資料來源、外部相依與揭露事項。每次演練只用一個模型；瀏覽器預設 headless，加上 `--headed` 才顯示視窗。僅限 Windows。設計記錄於 [ADR 0009](docs/adr/0009-exercise-on-a-disposable-target.md)。

**第一次演練之前**，執行 `/ask-codex:setup` 並要求它為演練做準備。它會以 `npm install --ignore-scripts` 把固定版本的瀏覽器 server（chrome-devtools-mcp 1.10.1）安裝到 `%LOCALAPPDATA%\ask-codex`，逐一比對 ask-codex 提交的 hash manifest，並檢查 node、Chrome（stable，149 以上）與你的 codex-cli 版本。接著它會啟動瀏覽器 server 一次，確認它能回應並列出工具，然後再結束它：它不呼叫任何瀏覽器工具，所以 Chrome 本身通常不會啟動，也不會留下任何 process、目錄或瀏覽器 profile。Chrome 第一次啟動是在每次演練的瀏覽器 guard。`%LOCALAPPDATA%\ask-codex` 只存放瀏覽器 server 與 guard 快取；刪除它即可移除兩者。

### 兩種模式

- **副本模式**（預設）：腳本把你的專案複製到一個新建立的可丟棄目標，並以你確認過的安裝與啟動指令從副本啟動 app（Claude 從專案檔案推導指令，並展開顯示 package script 與 lifecycle hook；腳本只原樣執行確認過的指令）。副本不含任何深度的版本控制資料（`.git`、`.hg`、`.svn`、`.jj`）、`.codex`、`.claude`、相依套件目錄（`node_modules`、`.venv`、`venv`、`__pycache__`、`.pnpm-store`）、`.env*` 檔與機密樣式檔（`*.pem`、`*.key`、`*.pfx`、`*.p12`、`id_*`、`credentials*`）。連結與 junction 會略過並列出，絕不跟隨或重建；alternate data stream 不會複製；預設超過 100,000 個項目或 2 GiB 的副本會失敗。env 檔只有在你為該次演練指名時才會進入副本，並列在報告的範圍行。app 使用副本自己的資料（種子檔、fixture、在副本中建立的測試帳號），除非你在該次演練的對話中說要用你的 dev 資料；此時報告第二行會註明。
- **接上模式**：你在該次演練的對話中要求時（例如「接上我正在跑的 dev server」），演練直接使用你已在執行的前端與後端。不複製、不安裝、不啟動，也絕不啟動、停止你的 server 或對它們發送訊號。Codex 仍在一個新建的空白可丟棄目錄中工作。專案檔案、memory 或先前的演練都不能選擇接上模式，而且接上模式一律視為使用你的 dev 資料。確認前，腳本會列出每個接上連接埠的擁有行程（command line 已遮蔽）；連接埠與其他行程共用、server 綁定所有介面或 IPv4-mapped 位址、擁有者是 System 行程（http.sys），或擁有者在封閉的轉發程式清單上（`wslrelay.exe`、`com.docker.backend.exe`、`com.docker.proxy.exe`、`vpnkit.exe`、任何 `svchost.exe`）時一律拒絕。演練期間每 2 秒檢查一次擁有者，有任何變化就停止演練。

**位址。**接上模式只接受 `127.0.0.1`。`[::1]` 與 `localhost` 會以一句固定的訊息拒絕：「Attach mode takes 127.0.0.1 only: the allowlist of chrome-devtools-mcp does not support [::1], so bind your dev server to 127.0.0.1.」，原因是 chrome-devtools-mcp 1.10.1 無法解析未跳脫的 `[::1]` URL pattern，而瀏覽器定義不帶任何反斜線。帶 scheme 的項目（例如 `https://…` 或 `wss://…`；接上模式只接受 http 的 `host:port`）以及 80、443 連接埠，則各以自己的訊息拒絕。副本模式接受 `127.0.0.1` 與 `localhost`；請求中也接受 `[::1]`，但 guard 會因同樣原因 fail closed，因此不會啟動 app。請把 dev server 綁定到 `127.0.0.1`（Vite `--host 127.0.0.1`、Next.js `-H 127.0.0.1`、Django `runserver 127.0.0.1:<port>`）。實測通過的 guard 都使用 `127.0.0.1` 位址。

**目標根目錄。**可丟棄目標建立在目標根目錄之下，而目標根目錄只能來自你：你的訊息、你的全域指示或你的 memory。專案自己的指示只能建議，Claude 會請你確認。腳本要求它是本機固定磁碟上的既有目錄，位於專案之外且不包含專案，不在 OneDrive 等雲端同步資料夾內，上層也沒有含 `.git` 或 `.codex` 的目錄；目標本身必須是新建立的，任何既有路徑都會被拒絕。

### 邊界

- **Codex** 使用與諮詢相同的固定值：唯讀 shell、`--ephemeral`、關閉 apps 與子代理、不能提升權限（`approval_policy="never"`、`approvals_reviewer="user"`）、不載入 execpolicy 規則（`--ignore-rules`），`-C` 指向可丟棄目標。不論你的 ask-codex 政策怎麼設定，其他所有 MCP server 都會停用；MCP 事前檢查要求剛好只有一個啟用的 server：本次演練以新名稱定義的瀏覽器 server。
- **瀏覽器 server** 是固定版本的 chrome-devtools-mcp 1.10.1，每次使用前都比對 hash manifest，並以 `node` 直接啟動（不經 `npx`、不經 shell），使用自己的工作目錄、自己的暫存目錄，以及一個為本次執行建立、封鎖下載、結束後移除的 Chrome profile。設定檔探索、使用統計、更新檢查、CrUX 查詢與 JavaScript 執行都關閉，網路標頭會遮蔽。Codex 只拿到 24 個列出的工具（頁面與瀏覽、snapshot 與截圖、點擊、hover、填寫、輸入、按鍵、拖曳、對話框、等待、調整大小、emulation、console 與網路清單、CSS 樣式、Lighthouse）；`upload_file`、`evaluate_script`、heap snapshot、performance trace，以及之後版本新增的任何工具都不開放。
- **逐一核准工具。**在 `approval_policy="never"` 下，Codex 會拒絕需要核准的 MCP 工具，所以演練只對列出的瀏覽器工具逐一預先核准（`tools.<tool>.approval_mode="approve"`，server 預設為 `prompt`）。這些鍵是指令列固定值，絕不會出現在 `ask`、`review` 或 `discuss`。瀏覽器工具能做到的範圍由下列設定限制並由 guard 檢查，而不是靠核准提示：Codex 的瀏覽器操作不會逐次審核。
- **網路限制。**Chrome 使用演練自己占用、一連上就關閉連線的 proxy 連接埠，只讓 app 的 host:port 繞過，再加上瀏覽器 server 針對這些 host:port 的 URL allowlist；WebRTC 只能走 proxy 的 UDP。這是 Chrome 設定加上 MCP allowlist，**不是 OS sandbox**。app 本身擁有完整網路。
- **檔案。**瀏覽器的寫檔工具只寫入 `<target>/evidence` 與本次執行自己的暫存目錄。截圖與 log 會隨目標一起刪除，除非你為該次演練要求把指定檔案保留到你指定的位置；由腳本搬移。
- **瀏覽器 guard。**在 app 啟動之前（接上模式：在 Codex 啟動之前），guard 不經 Codex 啟動同一份瀏覽器定義，並要求：app 的連接埠能載入；從圖片、iframe、fetch、WebSocket、Worker、`sendBeacon`、Service Worker 與重新導向送往其他 loopback 連接埠的請求——包括經由 `localhost`、`[::1]`、`127.0.0.2` 與 `0.0.0.0` 的寫法——都被擋下；送往其他網路介面位址與網際網路的請求失敗；WebRTC 不產生 server-reflexive candidate；`file:`、`chrome:` 等 URL 被拒絕或沒有作用；每個寫檔參數在各種路徑寫法（相對路徑、`..`、UNC、裝置路徑、短檔名、alternate stream、junction 與 symlink）下都留在允許的目錄內；每個列出的工具都存在。任何一項失敗，演練就停止，不啟動 app、不呼叫 Codex。通過結果在指紋（瀏覽器定義、node、套件 manifest、Chrome 路徑與版本、codex-cli 版本、Chrome policy 鍵）不變時最多沿用 12 小時。接上模式下，guard 先在自己的連接埠上執行，然後每次演練都（不使用快取）檢查實際接上的連接埠。**guard 證明的是瀏覽器能連到哪裡，不是 app 本身暴露或做了什麼。**
- **重現。**Claude 只透過腳本的 `repro` 操作重現 bug 論點，它以封閉的動作集合驅動同一個受限瀏覽器（在 app 位址內瀏覽、點擊、填寫、hover、按鍵、拖曳、回應對話框、等待文字、調整大小、snapshot、截圖、console 與網路清單）。集合以外的步驟——shell 指令、檔案操作、其他 URL——一律拒絕，該論點回報為未確認。
- **遮蔽。**Codex 回覆與重現輸出中類似 token 的字串——bearer 與 basic 憑證、JWT、`sk-`、`ghp_` 與 `xox` 樣式的金鑰、`token`、`key`、`secret` 或 `password` 後面的值、URL 中的使用者資訊、`--password`／`--token`／`--secret` 這類旗標的值——在 Claude 看到之前就被替換成 `[REDACTED]`。這是依樣式比對：其他形狀的機密可能漏過。
- **資料，不是指示。**Codex 的回覆與 app 顯示的一切都是資料：Claude 不會因為它們要求而執行指令、開啟 URL 或改動任何東西，並會在報告中記下這類要求。
- **結束。**`finish` 結束 Codex 的行程、瀏覽器，以及副本模式下 app 的行程（放在 Windows job object 中），逐一確認已結束，之後才移除可丟棄目標。無法確認結束的項目以 PID 與映像名稱回報，目錄保留並告知位置。被放著不管的演練，由 supervisor 在結果收集後 2 小時、或開始後 6 小時結束。supervisor 若終止，Codex 會在約 2 秒內被停止，副本模式下 app 的 job 也隨之結束。

### 與 Codex 自有瀏覽器的差別

Codex 的 Chrome 擴充功能與 in-app 瀏覽器只存在於 Codex 桌面應用，無法從 `codex exec` 使用；它們在你自己使用的瀏覽器中運作。`/ask-codex:ui` 從 `codex exec` 執行，給 Codex 一個獨立的 Chrome，使用本次執行專屬的 profile，看不到你的登入狀態、cookie、擴充功能或分頁，只能連到你的 app 位址，用完即丟——而且 Claude 會重現並判斷 Codex 的回報，而不是轉述。

### 固定版本

chrome-devtools-mcp 固定為 1.10.1，其 lockfile 與每個安裝檔案的 SHA-256 都提交在 `skills/ask/browser-server/`。提高版本就是一次發布，必須在 tag 之前重跑 P3–P5 與 P7 探測（`codex exec` 中的工具 allowlist、Codex 看得到截圖、allowlist 的拒絕方式、Service Worker 與其他網路外洩）以及 guard 檢查矩陣。演練以 `codex-cli 0.159.3` 測試；提高這個版本的發布必須重跑 B1 探測（瀏覽器工具的逐一核准）。使用其他 codex-cli 版本時，演練的確認訊息會告訴你：它核准瀏覽器工具的方式未經測試。

### 殘留風險與未驗證項目

- **只用於你自己的專案。**副本模式下，安裝與啟動指令會以你的身分、在任何 sandbox 之外、以完整網路執行你儲存庫的程式碼。app 行程樹以外的影響（container、服務）不在管理範圍內。
- **Codex 的 shell 連得到 localhost**，所有 ask-codex skill 都一樣（見下方「本機服務」）。接上模式下，它可以直接對接上的 server 送出任何請求，不受瀏覽器限制。報告會列出 Codex 提到接上主機、連接埠或 HTTP 用戶端的 shell 指令；這份清單只是警示線，不是防護。`-C` 不會讓 Codex 的唯讀 shell 看不到你的專案。
- **app 自身的開發工具**：從 app 位址可以使用的 in-browser console、debugger、開啟編輯器或提供檔案的端點（包括已知的 dev server 檔案服務漏洞），在兩種模式下都可能讓 Codex 以你的身分執行程式碼或讀取檔案。這會在確認訊息與報告中揭露，但不會阻止或偵測。
- **瀏覽器操作不會逐次審核：**app 因此做出的事（寄信、webhook、付款、資料變更）都會實際發生。Claude 會列出它找到的外部相依與整合，並在 app 啟動前詢問。
- **dev 資料與接上模式：**網路請求與回應的內容（含你的資料）可能送到 OpenAI。接上模式下副本模式的排除不適用，dev server 提供或顯示的任何內容（檔案、錯誤頁、環境變數值、你輸入的帳密）都可能送到 OpenAI；它的 proxy 與伺服器端請求會帶著你的 credentials 連到任何地方；可達性檢查與 Claude 的重現也會作用在你的真實資料上；你的 app 也可能因 Codex 的操作而改動你的 dev 資料與專案檔案。
- **接上模式的擁有者：**演練仰賴你確認哪些行程擁有接上的連接埠。封閉清單以外的轉發程式（`ssh -L`、`kubectl port-forward`）偵測不到，擁有者變更最多可能在 2 秒的輪詢間隔內未被發現。
- **supervisor 終止：**在 Codex 被停止前的幾秒內，proxy 連接埠沒有被占用。
- **本次執行專屬的暫存目錄：**瀏覽器 server 可以把 app 控制的內容寫入其中，而它同時存放隔離的 Chrome profile。
- **核准設定不可見：**`codex mcp get` 不會顯示 `tools.*.approval_mode`，所以 MCP 事前檢查無法檢查它；由每次新建的 server 名稱與離線指令列測試涵蓋。elicitation 的處理方式取決於 codex-cli 版本，你自行升級的 codex-cli 在發布重跑 B1 探測之前都未經測試。
- **固定值可被覆寫：**管理者層級的 Codex 設定（見「提升權限核准」）與 Chrome 企業政策可以覆寫這些固定值；guard 指紋包含 Chrome policy 鍵，政策一變就會重跑 guard。
- **未驗證：**DNS prefetch；headed 模式（`--headed`）；Windows 以外的平台（演練的所有操作都會在那裡拒絕執行）。

## 與官方 Codex plugin 的比較

OpenAI 官方 Codex plugin 也有審查指令，與 `/ask-codex:review` 是不同的工具：

| | `/codex:review` | `/codex:adversarial-review` | `/ask-codex:review` |
|---|---|---|---|
| 啟動者 | 僅限你 | 僅限你 | 僅限你 |
| Claude 如何處理輸出 | 逐字回傳，不加評論 | 逐字回傳，不加評論 | 判斷每個論點：採納、不採納或待查，並附理由 |
| 審查者 | Codex 內建的原生 reviewer | Codex，挑戰實作方式與設計選擇 | 透過 `codex exec` 呼叫 Codex，結構化論點 |
| Focus 文字 | 不支援 | 支援 | 支援，並附上 Claude 對變更意圖的說明作為立場 |
| 範圍 | working tree 或 branch（`--base <ref>`） | working tree 或 branch（`--base <ref>`） | working tree、`--base <ref>` 或 commit range |
| 模型與 effort | 可傳 `--model`（說明未記載）；不能選 effort | 可傳 `--model`（說明未記載）；不能選 effort | 模型簡稱與 effort，最多兩個模型並行 |
| MCP server | 指令本身不控制 | 指令本身不控制 | 預設停用（ask-codex MCP 政策）；Codex shell 唯讀；子代理關閉 |
| 前景與背景 | `--wait`、`--background`、`/codex:status` | `--wait`、`--background`、`/codex:status` | 前景執行，由腳本負責檢查間隔與停止回報 |
| 執行層 | plugin 共用的 companion 腳本 | plugin 共用的 companion 腳本 | 直接呼叫 `codex exec`（[ADR 0001](docs/adr/0001-call-codex-exec-directly.md)） |

想原封不動拿到 Codex 的原生審查結果，或要背景執行稍後再查，使用官方指令。想要一份由 Claude 先權衡、再決定是否採取行動的獨立第二意見審查，並自行選擇模型與 effort、控制 MCP server，使用 `/ask-codex:review`。兩者可以對同一份變更各跑一次。

## 驗證狀態

以下驗證記錄於 **2026-09-22**，涵蓋至實作提交 `7381fdc`：

| 檢查 | Windows／Git Bash | Linux／Ubuntu WSL |
|---|---|---|
| 公開 CLI 整合測試，使用 stub Codex | 25 項通過 | 25 項通過 |
| 行程生命週期檢查 | 39 項斷言通過（提高權限執行） | 46 項斷言通過 |
| 完整離線 Node 測試集 | 18 個測試檔通過 | 最後一次修正未重跑完整測試集 |
| 真實 Claude headless，使用 stub Codex | 未驗證 | 兩個聚焦案例通過，各執行一次 |
| 完整真實 Codex 諮詢 | 未驗證 | 未驗證 |
| 互動式 Claude 流程 | 未驗證 | 未驗證 |

使用 Python 3.11+ 與 Node.js 執行公開 CLI 及生命週期測試：

```bash
python evals/_harness/consultation_test.py
node evals/_harness/process-lifecycle.test.mjs
```

Linux 若以 `python3` 提供 Python 3.11+，請使用該指令。這些測試使用本機 stub 行程，不會呼叫 Codex 服務。生命週期測試會啟動與停止測試行程；Windows 的驗證結果取決於行程查詢權限。

兩個真實 Claude WSL 案例為 `script-consultation`（3/3 grader）與 `script-confirmation`（2/2 grader），各得分 1.00。它們在初版腳本主導實作期間執行，未在後續生命週期修正後重跑。另以真實 `codex mcp list` 獨立檢查過含點號 server 名稱的停用方式；該檢查沒有執行諮詢。

UI 演練（1.4.0）另外在 Windows 上驗證：使用 stub Codex 的離線測試（`python evals/_harness/exercise_*_test.py`，以及 Node 測試集中的 `ui-*` grader 檢查）；在 WSL 以 stub Codex 與 eval 平台替身執行的真實 Claude eval；不經 Codex、針對可丟棄 fixture app 的瀏覽器 guard（含每次只削弱一項限制、必須失敗的負向對照）、重現與接上模式實測；以及以真實 Codex 執行瀏覽器工具、量測逐一核准行為的 B1 探測。本次發布的實測驗收在 2026-10-17 完成，使用 codex-cli 0.159.3，共呼叫真實 Codex 三次。驗收在載入此 plugin 的 headless Claude Code session 中執行 `/ask-codex:ui`，對象是可丟棄的前端加後端 fixture：副本模式與接上模式各跑一次演練，之後再重跑一次副本模式。每一次都找到並重現了預先植入的 bug。前兩次顯示 Codex 其實沒有看到自己的截圖，因為帶 `filePath` 存檔的截圖只會回傳一行文字。框架 prompt 修正為「看畫面時不帶 `filePath`，存證據時才帶」之後，重跑的副本模式有 8 張截圖把影像回傳給 Codex。所有瀏覽器工具呼叫都沒有出現核准提示，Codex 的 shell 指令全為唯讀。存到 evidence 目錄內的截圖寫入成功，存到目錄外的則被拒絕。在接上模式中，使用者的 server 一直存活，識別資訊沒有改變。`config.toml` 沒有被更動，也沒有留下瀏覽器 profile 或演練程序。證據放在 `.scratch/exercise-skills/evidence/c7-live/`。互動式（非 headless）Claude Code 流程與 headed 模式沒有實測。

完整指令、報告、回歸歷程與待驗收項目見[驗證紀錄](.scratch/script-owned-consultation/evidence/validation.md)。舊版實作的歷史 eval 不能視為目前行為的證明。macOS 不在目前驗收範圍內。

## 已知風險與限制

- **MCP 設定競態（尚未解決）：**事前檢查與 `codex exec` 分別載入設定。檢查後新增的 server 沒有對應停用覆寫；已允許 server 的定義也可能在執行前改變。因此 guard 不提供原子化設定快照。準備與執行期間應保持 Codex 與 plugin 設定不變，但這項操作限制無法強制防止並行或惡意變更。詳見[調查紀錄](docs/mcp-configuration-race.md)。
- **MCP 存取：**允許的工具在 shell sandbox 之外執行，提示指示無法強制其唯讀；允許的 server 本身也可能啟動代理（例如 `codex mcp-server`），子代理的關閉旗標管不到它。唯讀 shell 本身也不會將讀取範圍限制為與問題相關的檔案。
- **請求來源：**Skill 規則要求諮詢與確認必須來自你的要求，但仍仰賴 Claude 遵循指示。早期測試曾在加入來源檢查前出現檔案文字觸發諮詢的情況；後續有限測試無法證明能完全抵禦提示注入。
- **行程快照：**追蹤涵蓋已觀測的子行程，包括已捕捉身份、後來脫離原群組的子行程，個別發送訊號前會檢查身份。若子行程在被觀測前已脫離並重新掛到其他父行程，可能無法發現。若 PID／群組被重用，且替代群組首領在觀測前已退出，剩餘群組可能被誤認為原群組並收到終止訊號。外掛沒有核心層強制的行程歸屬隔離。
- **停止未確認：**無法列舉或核對行程身份時，可能仍有行程存活，包含 Windows 行程查詢權限受限的情況。應保留回報的診斷資料；root 行程退出或 log 安靜，都不能單獨證明停止完成。
- **保留內容：**停止未確認時，會保留存活行程可能仍需使用的檔案。錯誤 log 可能含專案內容；診斷資料須在明確要求且確認停止後才會清理，沒有自動到期機制。
- **平台與設定：**歷史 Windows RAM disk 測試曾以 `os error 1` 失敗，但不能因此將所有 OS 錯誤都歸因於磁碟。長期信任專案的定義檢查尚未以真實 Codex CLI 完成端對端驗證。未選定 session 模型時，外部程式修改模型設定可能影響下一次諮詢。
- **子代理（1.3.2 修正；受影響版本 1.0.0–1.3.1）：**Codex 可以叫出子代理（預設開啟，目前多數模型使用 MultiAgentV2）。子代理的角色檔——例如 codex-feather 安裝的 `~/.codex/agents/*.toml`，或受信任專案的 `.codex/agents`——會自行設定 sandbox、模型與 MCP server，而且角色的 sandbox 會覆寫諮詢的 `-s read-only`。因此到 1.3.1 為止，諮詢可能叫出 `workspace-write` 的子代理，在你的專案寫入檔案、使用 ask-codex MCP 政策從未檢查過的 MCP server，並以角色的模型計費；事件紀錄最多只出現 `collab_tool_call` 的「wait」項目，看不到叫出子代理或子代理的寫入。自 1.3.2 起，每次諮詢都帶 `-c agents.enabled=false -c features.multi_agent_v2.enabled=false`。已在 codex-cli 0.159.3（Windows）以真實呼叫驗證：預設設定下的 v2 與 v1 模型，以及 `.codex/config.toml` 開啟 agents、MultiAgentV2、fan-out 與 multi_agent 的受信任專案——都沒有子代理工具、沒有寫入。未驗證：你自己的 Codex 設定開啟這些選項（指令列優先於設定檔）、較舊的 CLI、WSL。單獨使用 `--disable multi_agent` 擋不住 MultiAgentV2。若你在 1.3.1 以前曾對不可信的內容執行 `review` 或 `discuss`，且安裝了可寫入的角色，請在那些專案檢查 `git status`；並更新外掛（手動複製者請重新複製 skills）。
- **提升權限核准（1.3.3 修正；受影響版本 1.0.0–1.3.2）：**`codex exec` 在 headless 模式原本會拒絕所有核准請求，但當你的設定把 `approvals_reviewer` 解析為 `auto_review` 時會取消這個限制，核准請求改交給 Codex 的自動審查。因此到 1.3.2 為止，諮詢可能請求在唯讀 sandbox 之外執行指令並獲得核准：在 codex-cli 0.159.3（Windows）上，一次實測諮詢就以這種方式寫入了檔案。受信任專案的 `.codex/config.toml` 也能設定同樣的鍵。自 1.3.3 起，每次諮詢都帶 `-c approval_policy="never" -c approvals_reviewer="user"`，優先於你的設定與專案設定（依原始碼推論也優先於 profile，profile 未實測）。已在 codex-cli 0.159.3（Windows）以真實呼叫驗證：你的設定為 `auto_review`；受信任專案設定 `auto_review` 加上 `on-request`，或加上五種提示全部開啟的 granular 政策，並加上 `sandbox_mode = "workspace-write"`；以及不受信任的專案——都沒有請求提升權限、沒有寫入，`-s read-only` 也壓過了專案的 `sandbox_mode`（專案的 `default_permissions` 在有 `sandbox_mode` 或 `-s` 時會被 Codex 忽略，因此沒有單獨測到）。限制：每次實測中，模型在得知政策是 `never` 後都不送出提升權限請求，所以 Codex 在執行階段拒絕這類請求的行為沒有實際觸發過，某次權限請求的結果也只有模型自己的回報；`approvals_reviewer` 這個固定值是第二層防護，沒有單獨實測。未涵蓋：管理者層級的設定（舊版 managed config，或不允許 `never` 的 `requirements.toml`）可以覆寫或替換這些值。若你在 1.3.2 以前，於自己的設定或受信任專案的設定中設了 `auto_review` 並使用過諮詢，被核准的指令可能寫到你的帳號能寫的任何地方，不只是專案內：請檢查那些專案的 `git status` 以及其他你在意的檔案；並更新外掛。
- **execpolicy 規則（自 1.3.3）：**execpolicy `.rules` 檔中的 `allow` 規則（你的 `~/.codex/rules/`，在你選「don't ask again」時由 Codex 寫入；或受信任專案的 `.codex/rules/`）可能讓符合的指令不論核准政策都在 sandbox 外執行。這是從 Codex 原始碼推論，沒有實測。自 1.3.3 起諮詢帶 `--ignore-rules`，不載入你和專案的 `.rules` 檔——你自己的 `forbidden` 與 `prompt` 規則在諮詢中也不會套用；指令仍在唯讀 sandbox 內執行。未涵蓋：系統層級的規則（Windows 上的 `%ProgramData%\OpenAI\Codex\`）、管理者的 `prefix_rules`，以及 plugin 帶來的規則推測仍會載入（依 codex-cli 0.159.3 的靜態閱讀，未實測）。
- **本機服務：**在 Windows 上，唯讀 sandbox 擋對外網路但不擋 loopback（在 codex-cli 0.159.3、elevated sandbox 實測）。Codex 的 network proxy 設定會擋經過 proxy 連往 loopback 的請求，但繞過 proxy 的指令仍連得上。因此在每個 ask-codex skill——`ask`、`review`、`discuss` 與 `ui` 演練——中，Codex 的 shell 指令都可以對你機器上任何監聽 127.0.0.1 的服務發出請求，例如開發資料庫的管理介面。Codex 的設定無法防止這點；請讓敏感的本機服務需要驗證，或在對不可信內容進行諮詢時先停止它們。
- **sandbox 之外的其他工具：**唯讀的諮詢仍看得到會寫入 Codex 自身儲存的工具（`notes.write_file`／`append_to_file`、`create_goal`／`update_goal`）以及 `web.run`。它們不會動到你的專案檔案，但筆記會跨 Codex session 保留，網路存取則是對外通道；另行追蹤。
- **Codex `notify` hook 與其他 hook（刻意不修）：**使用者層設定的 Codex hook（以及受信任專案的 hook）也會在諮詢時執行，且不受 sandbox 限制。若 Codex 設定了 `notify`，諮詢時 Codex 也會執行該 hook。在 Windows 上，hook 會繼承這次執行的 prompt、事件與錯誤檔。hook 若比 Codex 活得久，就會一直鎖住這些檔案；曾觀察到一串 hook 鎖了約 13 秒。清理最多重試 30 秒（`ASK_CODEX_CLEANUP_WINDOW_S`），所以已完成的諮詢可能要等這麼久才回傳。鎖若超過這段時間，回覆仍會送達，並回報保留位置供之後清理。外掛不會停用你的 hook。詳見 [ticket 12](.scratch/script-owned-consultation/issues/12-cleanup-retries-transient-windows-lock.md)。
- **審查會讀取整個範圍：**審查讓 Codex 讀取範圍內的變更，working tree 審查包含 untracked 檔案。排除機密只是給 Codex 的指示，並非強制過濾。
- **Working tree 的 clean filter：**working tree 審查會執行 `git status`，當它重新讀取 stat 資料已變動的檔案時，仍可能執行儲存庫設定的 clean filter（`.gitattributes` 加上 `filter.<x>.clean`）。`--no-ext-diff`、`--no-textconv` 與 `core.fsmonitor=false` 都涵蓋不到這點。Base 與 range 審查只比較 commits，不受影響。審查不信任的儲存庫時，請用 `--base` 或 range，或先檢查其 filter 設定。
- **diff 內容引導：**被審查的變更中的文字可能試圖引導 Codex 的結論，被審查 repo 自己的 `AGENTS.md` 或 skills 也可能被 Codex 當成指示而非資料；「內容是資料」只是指示，並非強制。控制手段是 Claude 對每個論點的處置，且 Claude 不會在沒有你另行要求時依論點行動。
- **討論的用量與收斂：**每一輪討論呼叫一次 Codex（最多十次），且因為每輪都是新 session，Codex 每輪都要重新探索專案。避免假性共識的規則（讓步需附證據、標示後期翻轉、只接受阻擋等級的新論點）是給兩個模型的指示，不是強制機制；報告中的標示才是控制手段。Codex 先前的輸出會被帶入後續 prompt，和任何檔案一樣被視為資料。
- **用量：**諮詢會消耗 Codex 用量，並行諮詢會啟動兩次執行。目前尚未量測每次諮詢的 token 基本成本。
- **UI 演練：**它自己的殘留風險與未驗證項目列在 [UI 演練](#殘留風險與未驗證項目)。上方的「本機服務」風險同樣適用於演練。

報告可使用對話語言，但必須保留問題與類型、模型與 effort、生效 MCP 政策、相關計時與停止資訊，以及 Claude 對每個實質論點的處置。執行失敗不會被當成 Codex 意見。

## 授權

MIT，見 [LICENSE](./LICENSE)。
