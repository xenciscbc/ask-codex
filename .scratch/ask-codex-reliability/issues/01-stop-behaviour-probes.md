# 01 — 事實確認：停止行為的 probe 與 trace

**What to build:** 在動任何 skill 或 eval 檔案之前，把三個設計前提變成證據：停止後的殘留行程是否只發生在 headless session；停止報告缺漏是「從沒寫」還是「寫在中途、最後沒重述」；裸 `cd` 出現在哪一步。產出一份 evidence 檔（放在本 feature 目錄的 `evidence/` 下），供 03 與 06 的驗收引用。

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

**Type:** research

## 要做的事

1. **Live probe，互動式與 headless 各一次**（各消耗一次真實 Codex 呼叫）：以現行 skill 的 step 8 指令啟動一次諮詢（workspace 放 `D:\tmp\` 下的專用子目錄），呼叫 `TaskStop`，在 5 秒與 60 秒後比對 PID 集合（以 `^ProcessId` 錨定、與啟動前基線比較）與 `events.jsonl` 大小。前後各取一次 `config.toml` hash 與 `ask-codex.json` 是否存在。
2. **`--keep-temp` 重跑 `timeout-stalled-stop`**（`--runs 3`）：讀每個 run 的 `trace.jsonl`，記錄 `Consultation stopped:` 出現在哪一則訊息、是否出現在最終回覆。
3. **`--keep-temp --runs 5` 跑 `second-opinion-with-stance`**：從 trace 找出 `cd` 為第一個 token 的 Bash 指令，記錄它所處的 skill 步驟與前後文；未重現則記錄「5 跑未重現」。

## Acceptance criteria

- [ ] evidence 檔記錄兩次 live probe 的 PID 基線、停止後兩個時間點的 PID 集合、`events.jsonl` 大小變化，並給出結論：殘留行程發生於「headless」「互動式」或「兩者」。
- [ ] evidence 檔記錄 `timeout-stalled-stop` 三個 run 中 `Consultation stopped:` 的出現位置，並給出結論：缺漏屬於「從沒寫」或「寫了沒重述」（或三跑都有寫）。
- [ ] evidence 檔記錄 `second-opinion-with-stance` 五個 run 中裸 `cd` 的出現次數與所在步驟，或「未重現」。
- [ ] 所有 probe workspace 與 `--keep-temp` 保留目錄已刪除；`config.toml` hash 前後一致（Codex app 自行改寫的 runtime 欄位除外，需逐一列出）。
- [ ] 沒有改動任何 skill、eval 或 README 檔案。
