# 接續諮詢一律開新的 Codex session，不 resume

需要追問或複核時，ask-codex 開一個新的 `--ephemeral` Codex session，附上前一次的論點與 Claude 的處置，並把範圍鎖定在驗證這些論點；不使用 `codex exec resume` 延續原 session。依據是 Cross-Context Review（arXiv 2603.12123）：在全新 session 審查的 F1 是 28.6%，在同一個 session 重審一次只有 21.7%，是四種做法中最差的；multi-agent debate 研究也指出，保留 context 的多輪互動會出現 conformity 式的假收斂。代價是 Codex 每次都要重新探索專案，以及只存在於原 session 的推理脈絡會消失；換來的是不必保存 session 檔、不會在 Codex 歷史留下紀錄，也避開 resume 不支援 `-s` 時唯讀是否仍然生效這個未驗證的風險。

## Considered Options

- **Resume 原 session**（官方 `/codex:rescue --resume` 與 Codex MCP `codex-reply` 的做法）：省下重新探索的成本，但會錨定在 Codex 先前的立場上，每次諮詢都得保存 session，而且唯讀保證需要另外驗證。
- **新 session，不鎖定範圍**：每一輪都可能冒出新論點，讓反覆審查無法收斂。
