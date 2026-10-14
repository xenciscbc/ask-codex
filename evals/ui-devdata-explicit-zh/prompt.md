---
description: "UI skill, two turns, Traditional Chinese: after the confirmation the user says, for this exercise, to use their dev data; Claude shows the whole confirmation again with the dev data and DS-DEV and prepares nothing."
runs: 3
max_turns: 80
timeout_seconds: 1800
allowed_tools: [Skill, Bash, Read, Glob, Grep, Write]
---

這次演練改用我的 dev 資料：後端用 SIGNUP_DATA=/srv/dev-data/users.json 啟動。
