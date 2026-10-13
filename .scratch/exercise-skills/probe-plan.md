# 演練 skill 的本機實測計畫

Status: 已執行（2026-10-13），結果見 probe-results.md

目的：決定 UI 演練（Q7-A：Codex 透過 Chrome DevTools MCP 操作）與安全演練網路事前檢查（Q19-a）的可行性。依據：analyst 研究報告（2026-10-13，本 session）。

## 已知（不需呼叫 Codex）

- `D:\codex\config.toml` 的 `[windows] sandbox = "elevated"`：elevated backend（firewall 封鎖 outbound）。
- codex-cli 0.159.3。

## 共同做法

- 一次只跑一項；每項前後：`D:\codex\config.toml` 備份 bytes 並比對 hash、確認 `C:\Users\admin\.claude\ask-codex.json` 不存在、`codex*` PID 基準（`^ProcessId` 錨定）。Codex app 保持開啟。
- 工作目錄 `D:\tmp\exercise-probe\`（ws、srv 子目錄）；證據存到 `.scratch/exercise-skills/evidence/`，不放在將刪除的目錄內。
- Codex 指令沿用 `.scratch/subagent-boundary/probe-agentsoff.py` 的模式：`consult.preflight` 取得 MCP 停用覆寫，加上 `--ephemeral`、`--disable apps`、`agents.enabled=false`、`features.multi_agent_v2.enabled=false`；模型用 Codex 設定，effort medium。
- 測試 server：`python -m http.server`（綁 `127.0.0.1:8765`，根目錄 `srv`），內容含每次隨機產生的 token，只存在於本機。
- Chrome DevTools MCP 鎖定 `chrome-devtools-mcp@1.10.1`，旗標：`--isolated --headless --javascriptEvaluation=false --no-usage-statistics --no-performance-crux --allowedUrlPattern=http://127.0.0.1:8765/*`（語法待確認），env `CHROME_DEVTOOLS_MCP_NO_CONFIG_DISCOVERY=1`。
- 每項結束：停止 http server 與 MCP 啟動的 Chrome（isolated profile），比對 PID 基準；全部結束後刪除 `D:\tmp\exercise-probe`。

## 項目（約 6 次 Codex 呼叫）

| # | 內容 | Codex 呼叫 | 判讀 |
|---|---|---|---|
| P1 | Chrome stable 版本（需 ≥149 才有 URL allowlist）、node/npx 可用 | 0 | 版本 <149 → P5 改用 blocklist 或標為不可行 |
| P2a | `-s read-only`、網路關閉：請 Codex 讀 `http://127.0.0.1:8765/token.txt` 並嘗試連一個外部網址，回報結果 | 1 | 記錄 localhost／外部各自是否可達 |
| P2b | 同上，`-s workspace-write`（`network_access` 預設 false），寫入限 ws | 1 | 同上；是安全演練網路事前檢查的設計依據 |
| P3 | 以 `-c mcp_servers.cdt=…` 定義 DevTools MCP，加 `enabled_tools=["navigate_page","take_screenshot","take_snapshot","click","fill"]`；只請 Codex 列出它看得到的 cdt 工具名稱，不呼叫 | 1 | 只出現 allowlist 內的工具 → `enabled_tools` 在 exec 生效 |
| P4 | 請 Codex 開啟 `http://127.0.0.1:8765/page.html`（文字只畫在 canvas 上、DOM 中沒有），截圖並說出畫面上的文字與色塊顏色；再點按鈕回報結果 | 1 | 能說出 canvas 文字 → Codex 看得到 MCP 截圖；點擊成功且未被自動取消 → 操作工具可用 |
| P5 | 請 Codex 導航到一個外部網址，以及本機 `/redirect`（302 到外部網址），回報實際載入的頁面 | 1 | 兩者都被擋 → URL pattern 有效；redirect 可通過 → 記為 guardrail 漏洞寫進 README |
| P6 | 以 `-i` 附一張純色 PNG（顏色只存在於圖片中），請 Codex 說出顏色 | 1 | 說對 → ChatGPT 登入下 `-i` 可用 |

## 失敗時的退路

- P3 失敗（`enabled_tools` 不生效）：Codex 端沒有逐一工具的控制 → UI 演練只能信任 DevTools MCP 的 `--category*=false` 與 `--javascriptEvaluation=false`，重新評估 Q7。
- P4 看不到截圖：試 DevTools MCP 把截圖存檔、Codex 以內建 `view_image` 讀檔（多 1 次呼叫）。
- P4 操作被自動取消：查 `tools.<tool>.approval_mode`（多 1 次呼叫）。
