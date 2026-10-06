#!/usr/bin/env bash
# Ticket 10: compare the guards after an interactive check. Run from Git Bash after each test.
# Prints config.toml hash before/after, the user policy file state, Codex PIDs that were not
# there before (with their command lines), and the throwaway repository's status.
g=/d/tmp/discuss-interactive-guard
echo "config.toml before: $(cat $g/config.sha.before)"
echo "config.toml after : $(sha256sum /d/codex/config.toml | cut -d' ' -f1)"
ls /c/Users/admin/.claude/ask-codex.json >/dev/null 2>&1 && now=present || now=absent
echo "user ask-codex.json: before $(cat $g/user-policy.before), after $now"
tasklist //NH //FO CSV | grep -i codex | cut -d, -f2 | tr -d '"' | sort > $g/pids.after
new=$(comm -13 $g/pids.before $g/pids.after)
if [ -z "$new" ]; then echo "new codex pids: none"; else
  for p in $new; do echo "new codex pid $p: $(wmic process where ProcessId=$p get CommandLine 2>/dev/null | sed -n 2p | cut -c1-160)"; done
fi
echo "throwaway repo status:"; git -C /d/tmp/discuss-interactive status --short; echo "(end)"
