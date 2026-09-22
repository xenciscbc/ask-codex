# ask-codex

*[English version](./README.md)*

ask-codex 是 Claude Code 外掛，讓 Claude 透過本機 Codex CLI 向 OpenAI Codex 進行**諮詢**，取得獨立意見後由 Claude 自己逐點判斷。Codex 只回答，本身不會修改任何東西，但有一個例外值得先看下面的說明：MCP server 在 Codex 的唯讀 sandbox 之外執行。決策與所有改動都留在 Claude 與你身上——這是諮詢，不是**委派**。

Codex 以結構化的**論點**回覆，Claude 對每個論點給出**處置**——採納、不採納或待查——並附理由。

## 你可以依賴的範圍

原文（安全宣告以英文原句為準）：

> Codex's shell commands run read-only (writes denied, shell network blocked). MCP servers run outside that sandbox: by default all are disabled per consultation; servers you allow (or, in minimal-deny mode, all except node_repl/cua_repl) remain usable and may include tools that write or execute, limited only by instruction.

中文說明：Codex 的 shell 指令以唯讀執行（寫入被拒、shell 網路被擋）。MCP server 在該 sandbox 之外執行：預設每次諮詢全部停用；你開放的 server（或在最小停用模式下，除 `node_repl`／`cua_repl` 以外的全部）仍可使用，其中可能包含會寫入或執行的工具，只受指示限制。

## 安裝

複製此儲存庫後，以外掛方式載入：

```bash
claude --plugin-dir /path/to/ask-codex
```

headless 執行使用同一個旗標：

```bash
claude -p --plugin-dir /path/to/ask-codex \
  --permission-mode acceptEdits \
  --allowedTools Bash Read Glob Grep Skill Write TaskOutput TaskStop \
  "/ask-codex:ask Why does fetchUser return an empty object on timeout?"
```

headless 執行必須明確給出工具權限。腳本主導流程已透過 WSL Ubuntu 上的真實 Claude headless 搭配 stub Codex CLI 執行；這個範例尚未以真實 Codex CLI 完成端對端驗收。

從 GitHub 以 marketplace 外掛安裝的方式尚未實測——分支已經推送，但那條路徑從未被執行過，因此目前只有上面這個指令是已知可行的。

## 先決條件

- Python 3.11 以上版本。諮詢腳本使用標準函式庫的 `tomllib` 讀取 Codex 設定。
- Bash。Linux 直接使用 Bash；Windows 必須使用 Git Bash。
- 已安裝並登入的 Codex CLI。未登入時 Claude 會告訴你執行 `! codex login`。
- 舊版實作曾以 `codex-cli 0.154.0` 驗證。當時測試機器上的 `codex` 解析到 pnpm 安裝的 `@openai/codex`，而非 Codex 桌面應用自帶的執行檔——兩者都安裝時，實際使用的是 `PATH` 上的那一個。

## 使用方式

**手動諮詢。** 輸入 `/ask-codex:ask`（可附問題，也可不附），或直接用自己的話說「問一下 Codex」「聽聽 Codex 的看法」。提出要求本身即視為同意。沒有附問題時，Claude 會從對話推論出問題，並在送出前以一行揭示。ask-codex 不會自行諮詢 Codex：每一次諮詢都由你的要求開始。

**諮詢類型。** Claude 依上下文判斷：第二意見（檢驗並挑戰一份 Plan 或決策）、診斷（卡關時找出 root cause）、實作疑點審查（帶著具體疑點檢查某段實作或 diff）、技術問答，以及接續諮詢。診斷與技術問答採**盲測**送出——不透露 Claude 自己的假設，以免答案被錨定。

**模型與 effort。** 可用**模型簡稱**指定（`sol`、`astra`、`5.6 sol`），或連同 effort 一起指定（`sol:high`）；簡稱有歧義時 Claude 會列出候選並詢問。未指定模型時，Claude 會先用本 session 先前選定的模型，其次是 Codex 設定中的 `model`，再其次是 Codex 列出的模型中優先序最高的那一個。**諮詢 effort** 永遠不低於 `medium` 且一律明確傳入，不會沿用 Codex 設定裡的 effort。當你的**模型指定**與目前設定不同時，互動 session 會問這次指定只限這一次，還是延續本 session 其餘；headless 執行無法詢問，因此只套用於該次諮詢，並以對話語言在報告中揭露適用範圍，不要求固定句子或行位置。模型與 effort 和本 session 現行設定相同時，不需另加範圍說明。

**並行諮詢。** 指定兩個不同模型（`astra, sol`）可讓兩者回答同一個問題並各自給出**獨立意見**，再合併為**共識**、**單獨提出**與**分歧**三類，每個論點標註來源模型，每個分歧都說明採納哪一方及理由。最多兩個模型，且不可重複。

**接續諮詢。** 接續諮詢在全新的 Codex session 進行，附上前一次的論點與 Claude 的處置，並要求 Codex 逐項回報狀態；不會 resume 先前的 Codex session。

**腳本主導執行與長時間執行。** Claude 準備問題並判斷答案；`scripts/consult.py` 負責政策解析、事前檢查、安全組合指令、行程生命週期與結構化狀態。啟動前，它會提供可檢視的摘要，列出模型與 effort、專案目錄、允許的 MCP server 與生效政策。狀態會區分待確認、事前檢查失敗、執行中、完成、執行失敗、已確認停止與停止未確認；執行錯誤不會被當成 Codex 意見。

Claude 預設每 30 分鐘檢查一次進行中的諮詢；每段前景等待最多 60 秒，也不會超過該次檢查區間的剩餘時間。看起來停滯時，互動 session 會顯示已經過時間與最後事件，詢問要再等一輪還是停止；headless 執行會回報相同資訊並依既有停止路徑處理。只有在整棵行程樹經驗證已結束後，才會回報停止已確認。停止若無法確認，控制檔與診斷資料會保留，包含仍存活行程可能正在使用的檔案，並回報其位置。這些診斷資料沒有自動到期機制，只會在使用者明確要求清理後移除；log 仍可能含有專案內容。行程確認結束後，prompt 與 reply 會移除，不作為長期診斷資料保留。

**MCP 政策。** 預設每次諮詢停用所有 MCP server（**白名單模式**、空清單）。你可以開放特定 server，或改用**最小停用模式**，只停用 `node_repl` 與 `cua_repl`。設定記錄在使用者層與專案層的 **ask-codex 設定檔**，專案層覆蓋使用者層；`/ask-codex:setup` 會協助建立。政策檔不存在時採用文件記載的 fallback；既有政策檔若有無效 JSON、型別、政策值或 server 名稱，會在 Codex 啟動前採 fail-closed 中止。腳本在執行前檢查實際生效的 MCP 狀態，並把含點號的 server 名稱視為完整名稱處理。

專案定義的 server 必須取得明確的來源確認，而且確認綁定該次定義內容；command、argument、endpoint、environment 或其他定義欄位一旦改變，先前確認即失效。來源確認只表示認可該定義，允許使用 server 是另一個決定；Claude 可以在同一個問題中清楚分別詢問兩者。確認 ID 由準備完成的定義產生，本身不能構成同意。

## 驗證狀態

公開的 stub CLI 整合測試已在 Windows 與 Linux 執行：

```bash
python evals/_harness/consultation_test.py
```

2026-09-22，WSL Ubuntu 上的真實 Claude headless 各執行一次新的聚焦 eval，並使用 stub Codex CLI。`script-consultation` 的 3 個 grader 全部通過、score 為 1；`script-confirmation` 的 2 個 grader 全部通過、score 為 1：

```bash
evals/_harness/run-evals.sh --case script-consultation --runs 1 --allow-tools Bash Write
evals/_harness/run-evals.sh --case script-confirmation --runs 1 --allow-tools Bash Write
```

公開 CLI 測試在兩個平台各通過 25 項。程序生命週期結果、審查修正、指令載入量與剩餘缺口，見[驗證紀錄](.scratch/script-owned-consultation/evidence/validation.md)。較早的 eval 案例與歷史 Windows 實機結果只驗證舊版實作，不是目前的驗收證據。獨立使用真實 `codex mcp list` 的 probe 已驗證可停用含點號的 server 名稱，但尚未驗證使用真實 Codex CLI 的完整諮詢。互動式 Claude 流程也尚未驗證。macOS 不在目前支援的驗收範圍內。

## 已知風險

- 上面那句安全宣告就是全部範圍：唯讀只適用於 Codex 的 **shell 指令**，不涵蓋 MCP server。
- Codex 的 shell 讀得到你的帳號讀得到的任何檔案，範圍只由提示中的指示限制。
- 任何你開放的 MCP server 都在 sandbox 之外執行，可能包含會寫入或執行的工具。
- 誰可以發起諮詢，是 Claude 遵守的規則，不是外掛強制執行的：沒有 hook，也沒有工具層的阻擋。測試中，在加入「請求來源檢查」之前，曾有寫在檔案裡的文字讓 Claude 自行送出諮詢；加入檢查後，在少量的測試中沒有再出現，但這不能證明它不會發生。
- 停止未確認時，仍可能有行程存活。ask-codex 會回報不確定性並保留診斷所需的執行檔案，不會宣稱諮詢已結束。
- 每次諮詢在你的問題被考慮之前，大約就要 25k 輸入 token 的基本成本（此為設計文件的估算值，未實測）。

## 已知限制

- 位於 Codex Windows sandbox 無法執行的磁碟上的工作目錄無法諮詢。已知情況：RAM disk，`codex exec -C R:\…` 會以 `os error 1` 失敗。Claude 會回報失敗，不會編造答案。
- 被長期信任的專案仍仰賴腳本的專案定義檢查；此路徑尚未以真實 Codex CLI 完成端對端驗證。
- 外部程式可能在你工作期間改寫 Codex 設定中的 `model` 行，而你未指定模型時 Claude 就是讀那一行——因此相隔數分鐘的兩次諮詢，可能在你沒有任何動作的情況下使用不同模型。

報告可使用對話語言與自然措辭，不要求固定英文標題或固定行位置；但仍必須保留問題與諮詢類型、模型與 effort、生效 MCP 政策、相關計時與停止資訊，以及 Claude 對每個實質論點的處置。

## 授權

MIT，見 [LICENSE](./LICENSE)。
