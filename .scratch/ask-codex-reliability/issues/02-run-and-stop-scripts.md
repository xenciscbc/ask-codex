# 02 — 啟動與停止腳本，附離線測試

**What to build:** 隨 plugin 出貨兩支 bash 腳本，接手諮詢行程的生命週期：啟動腳本以前綴方式包住現有的 `codex exec …` 指令，把 Codex 起在自己的 process group、記下 pid、然後 wait；停止腳本殺掉整棵行程樹、驗證已結束、印出完整的停止報告行。不碰 skill 散文；這是讓 03 的改動變容易的 prefactor。

**Blocked by:** None — can start immediately（可與 01 平行）.

**Status:** resolved — implemented and tested on both platforms 2026-09-18 (see Comments)

## 行為

- **啟動腳本**：參數為 run directory 與 `--` 之後的完整指令。Linux 用 `setsid` 讓子行程自成 process group；Windows（Git Bash）找出子行程對應的 Windows pid。把 pid（與平台識別）寫進 run directory 的 `pid` 檔，然後 wait 子行程並回傳其 exit code。`codex exec` 指令與轉導由呼叫端寫在同一行，腳本不重組旗標。
- **停止腳本**：參數為 run directory 與模型才知道的報告欄位（生效的檢查間隔與來源、曾提供的選項與建議、並行時各模型狀態）。讀 `pid` 檔，Windows 用 `taskkill //T //F`，其他平台殺 process group；接著驗證 pid 已不存在、且 `events.jsonl` 的 mtime 在 5 秒觀察窗內不變。成功 exit 0 並印出以 `Consultation stopped:` 開頭的完整報告行（欄位見 spec）；失敗 exit 非零，報告行以 `process tree NOT confirmed — pids <…>` 收尾。不刪除 run directory。
- pid 檔缺失或指向不存在的行程時，走「NOT confirmed」分支，不得靜默成功。

## Acceptance criteria

- [x] 離線測試（放在 harness 既有的 node 測試旁，先例 `stub-modes.test.mjs`）對 stub 的 `slow-silent` 模式跑啟動腳本再跑停止腳本：`pid` 檔存在、停止後 `.stub/exec-finished` 不存在、`events.jsonl` 在觀察窗內不變、exit 0、報告行含 `process tree ended` 與全部欄位。
- [x] 同一測試覆蓋失敗分支：pid 檔缺失或指向不存在的行程時 exit 非零、報告行含 `process tree NOT confirmed`。
- [x] 並行欄位：帶 `done`／`still running` 參數時報告行末尾為 `; done — …; still running — …`；不帶時沒有這段。
- [x] 在 Windows Git Bash 與 WSL Ubuntu 各手動跑一次完整的啟動加停止（對 stub），兩邊都通過；結果記在本 ticket 的 Comments。
- [x] 腳本只依賴 bash 與各平台內建工具（Windows：`ps -W`、`taskkill`；Linux：`setsid`、`kill`），不需要 node 或 python。
- [x] harness 既有的所有 node 測試套件仍綠。

## Comments

**2026-09-18 — implemented as `skills/ask/scripts/run.sh` and `skills/ask/scripts/stop.sh`, test `evals/_harness/run-stop-scripts.test.mjs`.**

- `run.sh '<run dir>' -- <command…>`: starts the command as a background child (`setsid` on POSIX, so the child is its own process group and session; plain `&` on Git Bash, then the MSYS pid is mapped to the Windows pid through the `WINPID` column of `ps`), writes `pid=`, `platform=`, `started=` (epoch) and on Windows `msys_pid=` to `<run dir>/pid`, then `wait`s and exits with the child's code. The caller's redirections stay on the caller's line and are inherited, so the skill's step-8 command only gains the prefix.
- `stop.sh '<run dir>' --interval <T> --interval-source default|override --recommended wait|stop [--done … --still-running …]`: reads the pid file; Windows `taskkill //T //F //PID` (tree walked beforehand through `Get-CimInstance Win32_Process` parent links, survivors re-killed once); POSIX `kill -TERM` then `-KILL` on the group, the pid and every descendant; then a 5-second window in which `events.jsonl`'s mtime must not change. Prints exactly one `Consultation stopped:` line; the model-only fields come from the arguments, `elapsed`, `last event <type> <age> ago | no events` are computed from `started=` and `events.jsonl`. Exit codes: 0 ended; 1 survivors or `events.jsonl` still changing; 2 no usable pid file (`pids none recorded`); 3 pid not running. Never deletes the run directory.
- **Windows lesson recorded in the script:** `ps -W` does not list the bash that runs the stub once it has `exec`'d python (the first smoke run reported `not running` for a live pid), so the alive check uses `tasklist //NH //FI "PID eq <pid>"` and matches the pid in column 2 — its "no tasks" notice is localized. `taskkill //T //F` did end the bash → python chain in every run (the Probe C result held for this shape too).
- **Offline test** (19 checks): normal path on the stub's `slow-silent` mode with the real step-8 argument shape — pid file appears with all three keys, first events arrive, `stop.sh` exits 0 with a full-field line ending `process tree ended`, no parallel fields when none given, `run.sh` exits, `.stub/exec-finished` absent, `events.jsonl` size unchanged 1.5 s later, pid file kept; dead pid → non-zero, `NOT confirmed — pids 999999`, override/wait/elapsed/no-events fields; no pid file → non-zero, `pids none recorded`, parallel suffix `; done — gpt-6-astra; still running — gpt-5.6-sol` at the very end, and `done — none` passes through; missing arguments → exit 2 and no report line.
- **Manual runs:** Git Bash on Windows `node evals/_harness/run-stop-scripts.test.mjs` → 19 passed; WSL Ubuntu (node 20, `setsid` path) → 19 passed. Both platforms' full harness suites: every existing node test green except `ticket03-patterns.test.mjs`, which fails on both platforms *before* this ticket too — its `split(/
---
/)` cannot see the `---` separator in CRLF-checked-out `prompt.md` files (this checkout has `core.autocrlf=true`); unrelated to the scripts, left for a separate fix. `claude plugin validate` passes.
- Dependencies: bash plus `ps`/`tasklist`/`taskkill`/`powershell.exe` on Windows and `setsid`/`ps`/`kill` on Linux; no node or python in the scripts.
- Observed but out of scope: after `taskkill` the Windows `wait` returned 0 for the killed child, so `run.sh`'s exit code is not a reliable "was killed" signal on Windows; the skill judges a stopped run from the stop report, not from that code.

**2026-09-18 — reopened by slice 03 and closed again: cooperative stop added.** Slice 03's first reachability run showed `stop.sh: pid 7 is not running` — the eval sandbox gives every Bash command its own PID namespace, so a pid recorded by one command is invisible to the next (`pid=7`), and the direct kill can never work there. Fix (offline-tested first, per the slice's stop rule): `run.sh` now watches for `<run dir>/stop-request` while it waits and, from inside the child's namespace, kills the tree, verifies it and writes `<run dir>/stop-result` (`ended` or `survivors <pids>`); `stop.sh` always creates the request, additionally kills directly when the pid *is* visible, waits up to 10 s for the result, and counts the tree as ended when `run.sh` says so or when a visible pid's tree is gone; the 5-second `events.jsonl` window and the report line are unchanged. Shared tree helpers moved to `scripts/_tree.sh` (sourced by both). `run-stop-scripts.test.mjs` gained three cases — pid rewritten to an unknown value while `run.sh` is alive (must end via the request and print `process tree ended`), `run.sh` alone answering a request, and a dead pid with no `run.sh` (still `NOT confirmed`, and no `stop-result`) — **31 passed on Git Bash and 31 passed on WSL**. The dependency list is unchanged (bash plus platform tools).
