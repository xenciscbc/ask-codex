# 諮詢時的 MCP 政策：預設全停用、白名單、同名停用覆寫與事前檢查

Codex 的 `-s read-only` sandbox 只管 shell 指令，MCP server 在 sandbox 外執行（openai/codex#7635，closed not planned）；本機實測使用者設定與 plugin 帶來的 MCP（含可執行程式碼的 `node_repl`、可操作電腦的 `cua_repl`）在 `codex exec` 中都可用，且呼叫不需 approval。因此 ask-codex 預設在每次諮詢停用所有 MCP（白名單模式、空清單），使用者可在使用者層或專案層設定檔開放特定 server，或切換成只停用 `node_repl`／`cua_repl` 的 minimal-deny 模式；`/ask-codex:setup` 協助建立設定。停用機制採「同名停用定義」（`-c mcp_servers.<name>={command=…,enabled=false}`），因為官方記載的 plugin 層 key、plugin 停用與 feature 開關在 `exec` 中實測無效；此機制的優先順序未見官方文件，所以每次諮詢前都以 `codex mcp list --json` 做事前檢查，結果不符即中止。專案自己的 Codex 設定新增或改寫的 server 一律停用（或經使用者確認）；專案層 `.codex/config.toml` 內有 MCP 定義時則直接詢問、不同意即中止，不依賴覆寫優先順序。對外說法因此收窄為「Codex 的 shell 指令唯讀；MCP 依政策控制」，剩餘風險（被開放的 server 可能含寫入或執行工具、只受 prompt 指示限制；長期信任的專案未實測）記於 README。

## Considered Options

- **全部保留 MCP、只靠 prompt 指示**：最簡單，但 `node_repl`／`cua_repl` 可能被 prompt injection 誘導使用，且其他 server 也有寫入或執行工具。
- **只停用 `node_repl`／`cua_repl`（原 A+）**：保留為可選的 minimal-deny 模式，而非預設——盤點後發現其餘 server（`pencil`、`comfyui`、`blender`）也都不是純查詢。
- **`--ignore-user-config`**：能移除設定檔的 MCP，但同時丟掉 Windows sandbox 設定，導致所有指令都被 policy 擋下，Codex 無法自行查證。
- **逐一工具停用（`disabled_tools`）**：最精細，但需為每個 server 維護工具清單，列為範圍外。
