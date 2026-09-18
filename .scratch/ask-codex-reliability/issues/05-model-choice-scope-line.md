# 05 — 模型選擇效力的固定行（ticket 14）

**What to build:** 使用者指定的模型或 effort 與現行設定不同、且無法用 `AskUserQuestion` 詢問時，回覆固定有一行 `Model choice applies to this consultation only: <full model slug>, effort <effort>.`，每次都有；指定的選擇等於現行設定時，這行不出現。關閉 ticket 14。

**Blocked by:** 03（同樣改 step 10 第一項，避免兩張 ticket 同時改同一段；非功能依賴）.

**Status:** ready-for-agent

## 行為改動

- step 0 item 7 的「說出來」改為固定行，指向 step 10。
- step 10 第一項之後自成一行寫出該固定行（純文字，允許 markdown 強調包住固定字，但字、順序與值不可變）。
- 選擇等於現行設定時明文「不寫這行」。

## Acceptance criteria

- [ ] `alias-astra` 新增 regex grader（容忍 bold／backtick，要求完整 model slug 與 effort），與既有 `scope-note` llm grader 並列；`--runs 5` 全部 1.00。
- [ ] 對照案例（選擇等於現行設定的既有案例，或新增一個最小案例）斷言該行不存在，`--runs 3` 全過。
- [ ] 離線證明：regex 對正確回覆通過、對「只寫別名」「缺 effort」「改寫成句子」的改寫失敗。
- [ ] ticket 14 resolved，Comments 記錄五跑結果。
