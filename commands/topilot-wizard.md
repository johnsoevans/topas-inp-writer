Run the wizard, then build the refinement it describes. `$ARGUMENTS`, if given, is the workflow name.

## 1. Run the wizard

One Bash call, literal absolute path, **`run_in_background: true`**:

```
python C:/Users/dch0jse/.claude/skills/topas-inp-writer/scripts/topilot_wizard.py --from-claude
```

Append `--workflow $ARGUMENTS` only if `$ARGUMENTS` is non-empty. No `;` chaining and no variable assignment — either misses the permission allowlist prefix and prompts every run.

**`--from-claude` is required.** It tells the wizard you are waiting on it, so OK prints the job file to stdout. Without it the wizard assumes it was started standalone and opens a *separate* Claude CLI session on the job instead — two sessions, and this one gets nothing.

Background, not foreground, because **the Bash tool caps timeouts at 600000 ms (10 min)** while the wizard's watchdog runs to 30. A foreground call is killed at 10 minutes and takes the half-filled form with it — before the watchdog can save its partial job file, which is the one failure the watchdog exists to prevent. Backgrounding removes the cap; you are notified when the window closes.

The wizard prints the job file's path, then its JSON.

## 2. Exit codes

| Code | Do |
|---|---|
| 0 | Continue below |
| 1 / 2 / 3 | **Stop and report. Write no `.inp`.** |

Non-zero means error, cancelled, or timed out. A closed window must never become a plausible-looking file built from empty fields.

## 3. Build it

Invoke the **topilot-build** skill with the job file's path as its argument. If it is not available, read `~/.claude/commands/topilot-build.md` and follow it against that path.

That file is the single definition of how a job file becomes an `.inp` — it is also what a standalone wizard launch calls, so **never restate its rules here**; two copies drift.
