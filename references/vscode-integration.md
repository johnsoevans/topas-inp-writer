# Running the syntax checker from VS Code on the current file

`scripts/check_inp_syntax.py` is a plain command-line script, so the natural way to wire it into VS Code is a **task** bound to the currently open file — no extension required.

## Setup

Create (or add to) `.vscode/tasks.json` in the folder you have open in VS Code:

```jsonc
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "TOPAS: Check current INP file",
      "type": "shell",
      "command": "python",
      "args": [
        "C:\\PATH\\TO\\topas-inp-writer\\scripts\\check_inp_syntax.py",
        "${file}"
      ],
      "presentation": { "reveal": "always", "panel": "dedicated", "clear": true },
      "problemMatcher": {
        "owner": "topas-inp",
        "fileLocation": ["absolute"],
        "pattern": [
          { "regexp": "^=== (.*) \\[(PASS|WARN|FAIL)\\] ===$", "file": 1 },
          { "regexp": "^\\s*line (\\d+): (ERROR|warning): (.*)$", "line": 1, "severity": 2, "message": 3, "loop": true }
        ]
      },
      "group": { "kind": "build", "isDefault": true }
    }
  ]
}
```

Replace `C:\\PATH\\TO\\topas-inp-writer` with the actual location of the *extracted* skill folder on that machine — the script needs its own `references/` folder alongside it (it locates `21-keyword-index.md`, every chapter `.md` file, and `system-files/inc/` relative to its own path), so point at the real `scripts/check_inp_syntax.py` inside the unzipped skill, not a copy made elsewhere.

## Running it

Open any `.inp` file, **save it** (the script reads the file from disk, so unsaved edits in the editor buffer won't be checked), then either:
- press **Ctrl+Shift+B** (runs the default build task, since `"isDefault": true` is set above), or
- Command Palette → "Tasks: Run Task" → "TOPAS: Check current INP file"

Output appears in a dedicated terminal panel: `=== path [PASS/WARN/FAIL] ===` followed by any `line N: ERROR/warning: ...` entries, exactly as when run manually from a shell.

## The problem matcher (optional but recommended)

The `problemMatcher` block parses that same output and turns each `line N: ...` hit into a clickable entry in VS Code's Problems panel (Ctrl+Shift+M) that jumps straight to the line — on top of the plain terminal text, not instead of it. It's a two-part pattern: the first regex matches the `=== path [STATUS] ===` header line and captures the file path; the second (`loop: true`) matches each subsequent `line N: ...` entry and reuses that captured file path for all of them. This only needs to work for a single file per run (since the task always passes exactly `${file}`), which is why the simpler two-line pattern is reliable here rather than needing a full multi-file matcher.

## Things worth knowing

- If `python` isn't the right command on that machine (some setups use `python3` or `py` instead), change `"command"` accordingly — same requirement as running the script manually from a terminal.
- Ctrl+Shift+B is VS Code's normal "Run Build Task" shortcut. Setting `"isDefault": true` here makes this task the one that runs on that shortcut within this folder. If that shortcut is already used for something else in the same workspace, just trigger the task via the Command Palette instead of relying on the keybinding.
- This wires up the *current* file only. To check a whole folder at once, just run the script directly from a terminal against a directory (`python check_inp_syntax.py some_directory/`) rather than through this task.
