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

headless 執行必須明確給出工具權限；上面這組旗標就是實機驗收時使用的。

從 GitHub 以 marketplace 外掛安裝的方式尚未實測——分支已經推送，但那條路徑從未被執行過，因此目前只有上面這個指令是已知可行的。

## 先決條件

- 已安裝並登入的 Codex CLI。未登入時 Claude 會告訴你執行 `! codex login`。
- 實測版本為 `codex-cli 0.154.0`。測試機器上 `codex` 解析到 pnpm 安裝的 `@openai/codex`，而非 Codex 桌面應用自帶的執行檔——兩者都安裝時，實際使用的是 `PATH` 上的那一個。

## 使用方式

**手動諮詢。** 輸入 `/ask-codex:ask`（可附問題，也可不附），或直接用自己的話說「問一下 Codex」「聽聽 Codex 的看法」。提出要求本身即視為同意。沒有附問題時，Claude 會從對話推論出問題，並在送出前以一行揭示。ask-codex 不會自行諮詢 Codex：每一次諮詢都由你的要求開始。

**諮詢類型。** Claude 依上下文判斷：第二意見（檢驗並挑戰一份 Plan 或決策）、診斷（卡關時找出 root cause）、實作疑點審查（帶著具體疑點檢查某段實作或 diff）、技術問答，以及接續諮詢。診斷與技術問答採**盲測**送出——不透露 Claude 自己的假設，以免答案被錨定。

**模型與 effort。** 可用**模型簡稱**指定（`sol`、`astra`、`5.6 sol`），或連同 effort 一起指定（`sol:high`）；簡稱有歧義時 Claude 會列出候選並詢問。未指定模型時，Claude 會先用本 session 先前選定的模型，其次是 Codex 設定中的 `model`，再其次是 Codex 列出的模型中優先序最高的那一個。**諮詢 effort** 永遠不低於 `medium` 且一律明確傳入，不會沿用 Codex 設定裡的 effort。當你的**模型指定**與目前設定不同時，互動 session 會問這次指定只限這一次，還是延續本 session 其餘；headless 執行無法詢問，因此只套用於該次諮詢，回覆會以獨立的一行說明：`Model choice applies to this consultation only: <model>, effort <effort>.`。指定的模型與本 session 現行設定相同時，不會出現這一行。

**並行諮詢。** 指定兩個不同模型（`astra, sol`）可讓兩者回答同一個問題並各自給出**獨立意見**，再合併為**共識**、**單獨提出**與**分歧**三類，每個論點標註來源模型，每個分歧都說明採納哪一方及理由。最多兩個模型，且不可重複。

**接續諮詢。** 接續諮詢在全新的 Codex session 進行，附上前一次的論點與 Claude 的處置，並要求 Codex 逐項回報狀態；不會 resume 先前的 Codex session。

**長時間執行。** Claude 預設每 30 分鐘檢查一次進行中的諮詢。Codex 仍存活且持續產生事件時，Claude 會自行繼續等待並以一行告知。看起來停滯時，互動 session 會顯示已經過時間與最後事件及其存在時間，詢問要再等一輪還是停止；headless 執行無法詢問，因此會把同樣的資訊寫出來後直接停止。停止一次諮詢時，ask-codex 會結束它啟動的整棵 Codex 行程樹，並在確認 `events.jsonl` 不再變動後才回報已停止；若無法確認，報告會寫明「停止未確認」並列出仍存活的行程，由使用者處理。停止後不會有任何內容被歸給 Codex。外掛為此隨附幾支腳本：一支把 Codex 起成自己的行程樹並記錄下來，一支結束這棵樹並確認它已消失，一支在前景等待這次執行。最後這支在 headless 執行時很要緊：session 的工具裡若沒有 `TaskOutput`，就沒辦法「等通知」——turn 會在 Codex 還在跑的時候結束，回覆永遠沒人讀——所以 Claude 改成阻塞在等待腳本上，每段最多九分鐘。停止行為已在 Windows（Git Bash）以真實的 Codex CLI 實測，互動 session 與 headless 執行各一次；Linux 由腳本的離線測試與使用 stub 的 eval 套件涵蓋，沒有真實 Codex 的實測；macOS 未測。沒有 `TaskOutput` 時的等待，由 Windows 與 Linux 上的離線測試，以及以指示模擬該工具不存在的 stub eval 案例涵蓋（eval harness 無法真的把它拿掉）；尚未以真實的 Codex CLI 實測。

**MCP 政策。** 預設每次諮詢停用所有 MCP server（**白名單模式**、空清單）。你可以開放特定 server，或改用**最小停用模式**，只停用 `node_repl` 與 `cua_repl`。設定記錄在使用者層與專案層的 **ask-codex 設定檔**，專案層覆蓋使用者層；`/ask-codex:setup` 會協助建立。每次諮詢送出前，Claude 會重新列出 server 做 **MCP 事前檢查**，實際生效狀態與政策不符就中止。**專案定義的 server** 未經你具名確認一律不使用。

## 已知風險

- 上面那句安全宣告就是全部範圍：唯讀只適用於 Codex 的 **shell 指令**，不涵蓋 MCP server。
- Codex 的 shell 讀得到你的帳號讀得到的任何檔案，範圍只由提示中的指示限制。
- 任何你開放的 MCP server 都在 sandbox 之外執行，可能包含會寫入或執行的工具。
- 誰可以發起諮詢，是 Claude 遵守的規則，不是外掛強制執行的：沒有 hook，也沒有工具層的阻擋。測試中，在加入「請求來源檢查」之前，曾有寫在檔案裡的文字讓 Claude 自行送出諮詢；加入檢查後，在少量的測試中沒有再出現，但這不能證明它不會發生。
- 每次諮詢在你的問題被考慮之前，大約就要 25k 輸入 token 的基本成本（此為設計文件的估算值，未實測）。

## 已知限制

- 位於 Codex Windows sandbox 無法執行的磁碟上的工作目錄無法諮詢。已知情況：RAM disk，`codex exec -C R:\…` 會以 `os error 1` 失敗。Claude 會回報失敗，不會編造答案。
- 在 Codex 設定中被長期信任的專案，只由專案層的 fail-safe 涵蓋，未經實機測試。
- 大約每 5 到 10 次停止會有一次，`Consultation stopped:` 這一行只出現在最終回覆的開頭，而不是停止當下（eval 套件實測）。行程不論哪一種情況都會被結束。
- 外部程式可能在你工作期間改寫 Codex 設定中的 `model` 行，而你未指定模型時 Claude 就是讀那一行——因此相隔數分鐘的兩次諮詢，可能在你沒有任何動作的情況下使用不同模型。

## 授權

MIT，見 [LICENSE](./LICENSE)。
