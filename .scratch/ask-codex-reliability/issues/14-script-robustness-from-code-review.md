# 14 — 腳本的健壯性：code review（2026-09-22）延後處理的五項

**What to build:** `/code-review main`（Plan R07b S8，2026-09-22，effort high，範圍 `main...reliability/stop-path`）對 `skills/ask/scripts/` 提出七項 findings。兩項屬本分支引入的 P2，已在 merge 前修掉（`stop.sh`：旗標缺值時參數解析無窮迴圈；`exit-code` 已存在時不再殺行程——見 ticket 07 的 S8 Comment）。其餘五項在這裡逐項 triage。

**Blocked by:** 無。**Status:** needs-triage

## 項目

1. **殺之前不驗證 pid 的身分（P3）。** `stop.sh` 與 `_tree.sh` 只看 pid 是否存活；`pid` 檔裡的 `started` 從未拿來比對行程的建立時間。merge 前的修正已封住主要窗口（指令自己結束後 pid 被重用——此時 `exit-code` 存在，`stop.sh` 不殺任何東西）；剩下的窗口是 `run.sh` 自己被殺、沒寫出 `exit-code` 而 Codex 也已結束。修法：殺之前比對 CreationDate／start time 與 `started`。
2. **`win_tree` 只靠 `ParentProcessId` 建樹（P3）。** Windows 不會清除已死亡父行程的 pid：Codex 樹中某個 pid 若恰好等於某個長駐行程記錄的（早已死亡的）父 pid，該無關行程與其子樹會被算進 members、在 survivors 迴圈被 `taskkill /F`。修法：一併取 `CreationDate`，只接受建立時間晚於父行程的子行程。與第 1 項同類。
3. **macOS／BSD：行程樹只剩 root（P3）。** `ps -o pid= --ppid` 是 procps 專屬；macOS 預設沒有 `setsid`，`run.sh` 走不建 process group 的路徑；`kill -- -$root` 找不到 group、`ps -g` 為空、`posix_descendants` 為空（錯誤被 `2>/dev/null` 吃掉）。`node shim → codex` 的原生子行程若沒隨 SIGTERM 結束就成了孤兒，而 `stop.sh` 只檢查 root、仍回報 `process tree ended`。README 已寫明 macOS 未測；`_tree.sh` 檔頭「Linux/macOS — ps, kill, setsid」與實際不符。修法：`ps -ax -o pid=,ppid=` 加 awk 走訪（與 Windows 路徑同樣的做法），並在 macOS 上實測。
4. **`run.sh` 沒有 signal trap，watcher 沒有退出條件（P3）。** `run.sh` 若被 harness／`TaskStop` 殺掉而沒先走 `stop.sh`（使用者中斷、session 結束），已 `setsid` 的 Codex 不在被殺的 process group 內，會繼續跑完並消耗額度；只有 `run.sh` 這個 bash 被殺時，watcher subshell（`while sleep 0.5`）會一直輪詢 `stop-request`，run directory 被刪掉之後也不停。修法：`trap` TERM/INT/HUP 時 `tree_kill`；watcher 在 run directory 消失時退出。注意 ticket 10 的證據：headless session 結束時行程鏈是消失的——先量，再決定。
5. **pid 檔不可用時跳過了合作式停止（P3）。** Windows 上 `run.sh` 若在 5 次 `ps` 內拿不到 WINPID，會寫出 `pid=`（空值）；`stop.sh` 遇到空 pid 就直接 exit 2、不建立 `stop-request`，而 `run.sh` 的 watcher 也因 `[ -n "$root" ]` 為假而不殺任何東西——兩條停止路徑同時失效。`run.sh` 手上其實有 `msys_pid=$child`。修法：`stop.sh` 無論如何先寫 `stop-request`；`run.sh` 在 root 為空時退回 `kill "$child"`。
6. **「last event」取到巢狀的 `"type"`（P4）。** `stop.sh:65` 的 sed 是貪婪比對，抓的是該行最後一個 `"type"`：對 `item.completed` 得到 item 的 type（可接受），但 item 若含未跳脫的巢狀物件（`mcp_tool_call` 的 `"arguments":{"type":"object"}`），報告會寫成 `last event object`；type 含空白時 `stopped-line` 的 `\S+` 不匹配。

另記：`evals/_harness/ticket03-patterns.test.mjs` 在 `core.autocrlf=true` 的 checkout 上以 TypeError 失敗（以 `\n---\n` 切 CRLF 的 `prompt.md`）——既有、與本分支無關，memory 已有記錄；一行 `.replace(/\r\n/g, "\n")` 可修。

## Acceptance criteria

- [ ] 每一項有 disposition 與理由；要修的項目有離線測試（兩個平台），動到停止保證的有 live 的 `timeout-stalled-stop`／`headless-timer-stall` 回歸。
