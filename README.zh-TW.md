# ask-codex

*[English version](./README.md)*

ask-codex 是一組 Claude Code skills，也提供 plugin 安裝方式，透過本機 OpenAI Codex CLI 取得獨立意見。Claude 準備問題、判斷回覆，並對每個實質論點給出**採納、不採納或待查**的處置及理由。實作決策仍由你與 Claude 負責。

## 目前能力

- 五種諮詢類型：第二意見、診斷、實作疑點審查、技術問答與接續諮詢。診斷與技術問答不透露假設，降低答案被錨定的機會。
- 支援模型簡稱與明確的 reasoning effort；最多兩個不同模型各自回答。接續諮詢會開啟新 session，攜帶前次論點與處置。
- 腳本負責設定解析、MCP 授權檢查、執行、有時間上限的等待、行程追蹤與結構化結果。
- 安全傳遞 Unicode 回覆；輸出失敗可重新收集結果，並分開回報交付與清理失敗。
- 目前實作目標為 Windows 搭配 Git Bash，以及 Linux。兩者皆有離線測試；真實 Claude 的驗證目前僅涵蓋 WSL 上兩個搭配 stub Codex 的 headless 案例。此版完整的真實 Codex 諮詢與互動流程尚未驗證。

## 執行邊界

諮詢以 Codex 的唯讀 shell sandbox 執行，並封鎖 shell 網路存取。MCP server 在該 sandbox 之外執行；腳本預設停用事前檢查時觀察到的所有 server。檢查與執行之間的設定變更可能繞過檢查，詳見下方限制。你允許的 server 可能提供寫入或執行工具；外掛不會讓這些工具變成唯讀。

Skill 要求 Claude 只在你提出要求時諮詢，並將 Codex 輸出視為資料。這是模型指示，並非 hook 或工具層的授權屏障。行程停止也依賴可觀測的行程身份與快照，限制詳見下文。

## 安裝與更新

可選擇 marketplace plugin 或手動複製 skills；兩者都需要下方列出的先決條件。

### 方式一：從 GitHub 安裝 plugin

在 Claude Code 中加入此儲存庫的 marketplace，再安裝外掛：

```text
/plugin marketplace add xenciscbc/ask-codex
/plugin install ask-codex@ask-codex
```

第一個 `ask-codex` 是外掛名稱，第二個是此儲存庫定義的 marketplace 名稱。安裝後使用 `/ask-codex:ask` 與 `/ask-codex:setup`。

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
| `skills/setup/` | `~/.claude/skills/setup/` | `<project>/.claude/skills/setup/` |

Windows 的 `~` 是使用者家目錄，通常為 `C:\Users\<username>`。`ask` 必須包含 `SKILL.md`、`prompts/`、`scripts/` 與 `consultation.schema.json`，不能只複製 `SKILL.md`。`setup` 提供 MCP 政策設定輔助功能。

使用上述目錄名稱時，指令是 `/ask` 與 `/setup`，取代本 README 其他段落中的 plugin 前綴指令。也可以直接用自然語言明確要求 Claude 諮詢 Codex。參考 Claude Code 的[skill 位置與命名規則](https://code.claude.com/docs/en/skills)。

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
- 舊版實作曾以 `codex-cli 0.154.0` 驗證。當時測試機器上的 `codex` 解析到 pnpm 安裝的 `@openai/codex`，而非 Codex 桌面應用自帶的執行檔——兩者都安裝時，實際使用的是 `PATH` 上的那一個。

## 使用方式

```text
/ask-codex:ask 為什麼 fetchUser 逾時時會回傳空物件？
/ask-codex:ask sol:high 檢查這份 diff 的重試邏輯。
/ask-codex:ask astra, sol 對這份計畫提供第二意見。
/ask-codex:setup
```

簡稱會對照本機 Codex 模型清單解析；範例不代表你的帳號一定可使用這些模型。

**手動諮詢。** 輸入 `/ask-codex:ask`（可附問題，也可不附），或直接用自己的話說「問一下 Codex」「聽聽 Codex 的看法」。提出要求本身即視為同意。沒有附問題時，Claude 會從對話推論出問題，並在送出前以一行揭示。Skill 要求每次諮詢都必須來自你的要求；實際約束範圍如上所述。

**諮詢類型。** Claude 依上下文判斷：第二意見（檢驗並挑戰一份 Plan 或決策）、診斷（卡關時找出 root cause）、實作疑點審查（帶著具體疑點檢查某段實作或 diff）、技術問答，以及接續諮詢。診斷與技術問答採**盲測**送出——不透露 Claude 自己的假設，以免答案被錨定。

**模型與 effort。** 可用**模型簡稱**指定（`sol`、`astra`、`6 sol`），或連同 effort 一起指定（`sol:high`）；簡稱有歧義時 Claude 會列出候選並詢問。未指定模型時，Claude 會先用本 session 先前選定的模型，其次是 Codex 設定中的 `model`，再其次是本機快取中可見且優先序最高的模型；這些來源都沒有模型時，交由 CLI 使用預設值。**諮詢 effort** 永遠不低於 `medium` 且一律明確傳入，不會沿用 Codex 設定裡的 effort；`ultra` 需要使用者明確要求且模型支援。當你的**模型指定**與目前設定不同時，互動 session 會問這次指定只限這一次，還是延續本 session 其餘；headless 執行無法詢問，因此只套用於該次諮詢，並以對話語言在報告中揭露適用範圍，不要求固定句子或行位置。模型與 effort 和本 session 現行設定相同時，不需另加範圍說明。

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

例如，下列政策只允許名為 `docs`、且已在 Codex 啟用的 server：

```json
{"mcp_policy": "allowlist", "mcp_allow": ["docs"]}
```

Setup skill 只寫入 ask-codex 政策檔，不會修改 Codex 的 `config.toml`。專案本機政策應排除於版本控制之外。準備階段可能要求對專案政策或 server 使用權限進行 session 確認；headless 若仍有待確認事項，就不會執行諮詢。

專案定義的 server 必須取得明確的來源確認，而且確認綁定該次定義內容；command、argument、endpoint、environment 或其他定義欄位一旦改變，先前確認即失效。來源確認只表示認可該定義，允許使用 server 是另一個決定；Claude 可以在同一個問題中清楚分別詢問兩者。確認 ID 由準備完成的定義產生，本身不能構成同意。

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

完整指令、報告、回歸歷程與待驗收項目見[驗證紀錄](.scratch/script-owned-consultation/evidence/validation.md)。舊版實作的歷史 eval 不能視為目前行為的證明。macOS 不在目前驗收範圍內。

## 已知風險與限制

- **MCP 設定競態（尚未解決）：**事前檢查與 `codex exec` 分別載入設定。檢查後新增的 server 沒有對應停用覆寫；已允許 server 的定義也可能在執行前改變。因此 guard 不提供原子化設定快照。準備與執行期間應保持 Codex 與 plugin 設定不變，但這項操作限制無法強制防止並行或惡意變更。詳見[調查紀錄](docs/mcp-configuration-race.md)。
- **MCP 存取：**允許的工具在 shell sandbox 之外執行，提示指示無法強制其唯讀。唯讀 shell 本身也不會將讀取範圍限制為與問題相關的檔案。
- **請求來源：**Skill 規則要求諮詢與確認必須來自你的要求，但仍仰賴 Claude 遵循指示。早期測試曾在加入來源檢查前出現檔案文字觸發諮詢的情況；後續有限測試無法證明能完全抵禦提示注入。
- **行程快照：**追蹤涵蓋已觀測的子行程，包括已捕捉身份、後來脫離原群組的子行程，個別發送訊號前會檢查身份。若子行程在被觀測前已脫離並重新掛到其他父行程，可能無法發現。若 PID／群組被重用，且替代群組首領在觀測前已退出，剩餘群組可能被誤認為原群組並收到終止訊號。外掛沒有核心層強制的行程歸屬隔離。
- **停止未確認：**無法列舉或核對行程身份時，可能仍有行程存活，包含 Windows 行程查詢權限受限的情況。應保留回報的診斷資料；root 行程退出或 log 安靜，都不能單獨證明停止完成。
- **保留內容：**停止未確認時，會保留存活行程可能仍需使用的檔案。錯誤 log 可能含專案內容；診斷資料須在明確要求且確認停止後才會清理，沒有自動到期機制。
- **平台與設定：**歷史 Windows RAM disk 測試曾以 `os error 1` 失敗，但不能因此將所有 OS 錯誤都歸因於磁碟。長期信任專案的定義檢查尚未以真實 Codex CLI 完成端對端驗證。未選定 session 模型時，外部程式修改模型設定可能影響下一次諮詢。
- **Codex `notify` hook（刻意不修）：**若 Codex 設定了 `notify`，諮詢時 Codex 也會執行該 hook。在 Windows 上，hook 會繼承這次執行的 prompt、事件與錯誤檔。hook 若比 Codex 活得久，就會一直鎖住這些檔案；曾觀察到一串 hook 鎖了約 13 秒。清理最多重試 30 秒（`ASK_CODEX_CLEANUP_WINDOW_S`），所以已完成的諮詢可能要等這麼久才回傳。鎖若超過這段時間，回覆仍會送達，並回報保留位置供之後清理。外掛不會停用你的 hook。詳見 [ticket 12](.scratch/script-owned-consultation/issues/12-cleanup-retries-transient-windows-lock.md)。
- **用量：**諮詢會消耗 Codex 用量，並行諮詢會啟動兩次執行。目前尚未量測每次諮詢的 token 基本成本。

報告可使用對話語言，但必須保留問題與類型、模型與 effort、生效 MCP 政策、相關計時與停止資訊，以及 Claude 對每個實質論點的處置。執行失敗不會被當成 Codex 意見。

## 授權

MIT，見 [LICENSE](./LICENSE)。
