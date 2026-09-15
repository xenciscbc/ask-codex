# 直接呼叫 `codex exec`，不依賴官方 codex plugin

ask-codex 直接呼叫 `codex exec`，不重用官方 codex plugin 的 `codex-companion.mjs task`。companion 會把 ask-codex 綁在「有安裝官方 plugin」的環境，而且它的 prompt 包裝與輸出格式不在我們控制之下；直接呼叫則能自己決定 `-s read-only`、`--ephemeral` 與 `--output-schema`，讓 Codex 回傳 Claude 可逐點判斷的結構化意見。代價是 Codex CLI 參數異動時要自行跟進。
