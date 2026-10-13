# 演練 skill 本機實測結果（2026-10-13）

環境：Windows 11、codex-cli 0.159.3、`[windows] sandbox = "elevated"`、Chrome 154.0.8037.98、node v24.12.0、chrome-devtools-mcp 1.10.1、模型 gpt-5.6-sol / medium。證據：`evidence/`（argv、events、stderr、last message、server access log、tokens）。腳本：`probe-run.py`、`probe-server.py`、`probe-mcplist.py`、`probe-mcp-stdio.py`。

| # | 結果 | 證據 |
|---|---|---|
| P1 | Chrome 154（≥149，URL allowlist 可用）；node/npx 可用 | registry BLBeacon |
| P2a | `-s read-only`：localhost 可達（access log 有請求，原始輸出含完整 token）；外部 `curl: (7) Failed to connect` | p2a-*；與 openai/codex#48856 描述一致 |
| P2b | `-s workspace-write`（network_access 預設 false）：同 P2a；未寫入任何檔案 | p2b-* |
| P3 | `-c mcp_servers.cdt.enabled_tools=[…]` 在 exec 生效：只出現 6 個 allowlist 工具；呼叫清單外的 `list_pages`、`new_page` 得到 `TypeError: tools.mcp__cdt__… is not a function` | p3d-* |
| P4 | Codex 看得到 MCP 截圖：說出橘色 banner 與只存在於 SVG 圖片中的 `ORCHID-5266`（banner.svg 只在頁面載入時被請求一次）；click 成功、未被自動取消，讀到 `3c5ade4a`；沒有 shell 指令 | p4-*、access.log |
| P5 | `--allowedUrlPattern=http://127.0.0.1:8765/*`：直接導航外部 → `blocked by blocklist/allowlist rules`；本機 302 到外部 → `net::ERR_INTERNET_DISCONNECTED`，未載入外部內容。同時主機本身可連 example.com（200） | p5-* |
| P6 | `-i` 附 PNG 在 ChatGPT 登入下可用：左 teal `#147D70`（實際 `#0f766e`）、右 magenta `#C325D3`（實際 `#c026d3`） | p6-* |

## 附帶發現

- **MCP 工具是延遲載入的**：只問「列出你的工具」時 Codex 回答看不到任何 `cdt` 工具（p3、p3b），要提示它先用 discovery 才找得到（p3c、p3d）。演練的 framing 必須告訴 Codex 先 discover。
- **Codex 轉述會出錯**：P2b 中 Codex 回報的 token 少了最後一個字元，原始指令輸出是完整的。支持 Q9/Q13「Claude 自行重現才算證實」。
- **`codex sandbox <cmd>` 可在不呼叫模型的情況下以 Codex sandbox 執行指令**：read-only 與 `-c sandbox_mode="workspace-write"` 下外部連線都被擋。可作為網路事前檢查的機制（是否與 `codex exec` 的 sandbox 完全相同，未證實）。
- MCP server 用 `cmd /c npx -y chrome-devtools-mcp@1.10.1 …` 在 Codex 的預設 MCP 環境下可正常啟動，不需額外 env。

## P7：哪些請求類型逃得出 `--allowedUrlPattern`（不呼叫 Codex）

`probe-leaks.py` 直接以 stdio 驅動 MCP（node 啟動，`cmd /c` 會把 `<`、`>` 當重導向），8765 為允許來源、8766 為「不允許來源」替身，頁面以各種方式連 8766 與 https://example.com/，以 server 端紀錄判讀。證據：`evidence/p7-leaks-final.json`（最後一組）與本段表格。

| 設定 | img / iframe / fetch / WebSocket / Worker / sendBeacon → 8766 | Service Worker → 8766 | 頁面 → 外部 | Service Worker → 外部 |
|---|---|---|---|---|
| 無 allowlist（對照） | 全部送達 | 送達 | 成功 | 成功 |
| allowlist | 全部擋下 | **送達** | 擋下 | **成功** |
| allowlist + `--proxyServer=http://127.0.0.1:9`（不存在的 proxy） | 擋下 | **送達**（loopback 預設不走 proxy） | 擋下 | 擋下 |
| allowlist + 死 proxy + `--chromeArg=--proxy-bypass-list=<-loopback>;127.0.0.1:8765` | 擋下 | 擋下 | 擋下 | 擋下 |

- 受測頁面在最後一組仍正常載入（回報請求送達 8765）。
- `--chromeArg=--disable-features=ServiceWorker`、`--disable-service-worker`、`--disable-features=ServiceWorkerServicification,ServiceWorkerOnUI` 都關不掉 Service Worker。
- 結論：URL allowlist 單獨使用時 Service Worker 是漏洞；加上「死 proxy + 只讓受測 host:port 直連」後，本次測到的所有請求類型都被 Chrome 網路層擋下。受測 app 有多個 port（例如前端 5173、後端 8080）時，bypass list 要列出每一個。

### P7b：WebRTC（UDP）

頁面建立 `RTCPeerConnection`，STUN server 為 `127.0.0.1:3478`（本機 UDP listener，「不允許來源」替身）與 `stun.l.google.com:19302`（真實外部），以回報到 8765 的 candidate 類型判讀：`srflx` = UDP 到達外部 STUN 並取得回應。

| 設定 | 結果 |
|---|---|
| 無 allowlist（對照） | `host` + `srflx` candidate；本機 UDP listener 收到封包 → UDP 可達外部與本機其他 port |
| 只有 allowlist | 只有 `host`；無 `srflx`；listener 未收到 → UDP 被擋 |
| allowlist + 死 proxy（無 bypass list） | 同上 |
| allowlist + 死 proxy + bypass list | 同上 |
| 上一列 + `--chromeArg=--force-webrtc-ip-handling-policy=disable_non_proxied_udp` | 同上 |

- WebRTC 的 UDP 在只有 allowlist 時就被擋下，機制未查明（觀察結果，非文件保證）；policy 旗標無副作用，建議一併加上作為第二層。
- `host` candidate 只是本機網卡位址的列舉，沒有送出封包；會讓頁面得知本機 IP，受測頁面是使用者自己的 app，影響可忽略。

## P8：Codex network proxy 能否限制 shell 的 loopback（Q29/Q30）

兩個 server：127.0.0.1:8765、:8766。設定共同部分：`default_permissions="probe"`、`permissions.probe.extends=":read-only"`、`network.enabled=true`、`features.network_proxy.enabled=true`、`allow_local_binding=false`，不帶 `-s`（文件：不可與 sandbox_mode 併用）。證據：`evidence/netprobe-1.txt`、`evidence/p8a-*`、`evidence/p8c-*`。

- `codex sandbox <cmd>`：四種設定下 loopback 兩個 port 都可達、沒有任何 PROXY 環境變數 → 這個除錯指令不啟動 proxy，結果不代表 exec。
- **P8a（exec，無 allow 規則）**：proxy 有啟動（`CODEX_NETWORK_PROXY_ACTIVE=1`、`HTTP_PROXY=http://127.0.0.1:3128`…）；第一次 `curl` 127.0.0.1 與 example.com 被擋（"local/private network addresses are blocked"、"domain is not on the allowlist"），**但同一指令立刻自動重跑並成功**：8765、8766、example.com（200）全部可達。原因：使用者設定 `approvals_reviewer = "auto_review"`。
- **P8c（P8a + `approval_policy="never"`）**：經 proxy 的 loopback 與外部都被擋且不再放行；**`curl --noproxy "*"` 直連 127.0.0.1:8765、:8766 仍成功**。

結論：
1. 在本機（Windows elevated backend、codex-cli 0.159.3）上，Codex 設定無法阻擋 shell 直連 loopback；文件「繞過 proxy 的 loopback client 會被 OS sandbox 擋下」不成立（與 openai/codex#48856 一致）。
2. `codex exec` 原本在 headless 模式強制 `approval_policy = Never`，但**當設定的 `approvals_reviewer` 解析為 `auto_review` 時會丟掉這個強制**（`codex-rs/exec/src/lib.rs`，見 build_exec_config 的 fallback），核准政策改由設定檔決定，核准請求交給自動審查模型。P8a 中網路核准即因此被自動放行。現行諮詢指令沒有固定 `approval_policy`；它在 `-s read-only` 下是否也能透過自動審查取得提升權限，**未實測**。

## P9：現行諮詢指令下的提升權限（Q32）

- p9：與 consult.py 相同的命令列（`-s read-only`、無 `approval_policy`）：寫檔被拒 → Codex 請求提升權限 → **自動審查核准，檔案寫入**。
- p9b：同上加 `-c approval_policy="never"`：Codex 不能請求提升權限，檔案未寫入。
- 已發布版本的安全缺口，另開 `.scratch/approval-boundary/issues/01-auto-review-escalation-breaks-read-only.md`。演練 skill 必須固定 `approval_policy="never"`。

## 未測

- DNS prefetch。
- headful（開視窗）模式。
- `codex sandbox` 與 `codex exec` 的 sandbox 是否等價。

## 清理

probe server 已停止；未發現殘留的 MCP Chrome（無 headless/puppeteer 行程）；`D:\codex\config.toml` hash 前後相同（`eedf06aa…`）；`C:\Users\admin\.claude\ask-codex.json` 不存在；`D:\tmp\exercise-probe` 已刪除。
