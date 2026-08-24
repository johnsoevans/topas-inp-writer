# Plan: distribute `/topilot-*` slash commands alongside the skill

## Goal

Ship a handful of custom slash commands (e.g. `/topilot-wizard`, `/topilot-build`) as
part of the normal install/update flow, so users get them for free alongside the
`topas-inp-writer` skill — without ever clobbering a command file a user created
themselves.

## Decision

Files land **flat** in `.claude/commands/`, not in a namespaced subfolder.

- A subfolder (`.claude/commands/topas-inp-writer/foo.md`) would force Claude Code
  to invoke it as `/topas-inp-writer:foo` — breaks the requirement that users can
  just type `/topilot-wizard`.
- Collision risk from going flat is acceptable because the filenames are already
  project-specific (`topilot-wizard.md`, `topilot-build.md`, ...). A user having an
  unrelated pre-existing command with the exact same name is effectively impossible.
  No ownership-marker/collision-check machinery is needed — the distinctive prefix
  is the safety mechanism.

## Repo-side changes (`topas-inp-writer`, this repo)

1. Add a `commands/` folder at the repo top level, containing one `.md` file per
   command (e.g. `commands/topilot-wizard.md`, `commands/topilot-build.md`), using
   normal Claude Code custom-slash-command format (frontmatter + prompt body).
2. Update the release zip build so `commands/` ships as a sibling to the existing
   skill payload (`SKILL.md`, `references/`, `scripts/`, `example_inp_files/`) —
   check `.github/release-exclude.txt` and whatever step assembles the zip in
   `.github/workflows/release.yml`. `commands/` should **not** end up nested inside
   the `topas-inp-writer/` skill folder in the zip; it should be a top-level
   sibling entry so the installer can pick it out separately.
3. Update `README.md` repo-layout section to mention `commands/`.

## Installer changes (`topas-editor-extension`, `TopasAisetup.ts` — separate repo)

1. After extracting the release zip, in addition to placing the skill payload at
   `.claude/skills/topas-inp-writer/`, copy every file from the zip's `commands/`
   folder into `.claude/commands/` **flat** (strip the `commands/` prefix, keep
   filenames as-is: `commands/topilot-wizard.md` → `.claude/commands/topilot-wizard.md`).
2. Overwrite unconditionally on install and update — no need to check for existing
   files first, per the collision-risk reasoning above.
3. (Nice-to-have, not required for v1): if a future release renames or drops a
   `topilot-*.md` command, an unconditional "overwrite what we ship" install won't
   remove the old orphaned file. If that happens, either have the installer
   explicitly delete known-removed filenames on update, or write a small manifest
   of previously-installed command filenames alongside the install so it can
   reconcile (delete anything it installed before that isn't in the new set).
   Skip this until it's actually needed.

## Out of scope / considered and rejected

- Namespaced subfolder under `.claude/commands/` — rejected, breaks short invocation
  names (see Decision above).
- Ownership-marker comments in shipped command files to detect "is this ours"
  before overwriting — unnecessary given how specific the `topilot-*` prefix
  already is; would just be extra complexity for no real safety gain.
- Moving to the full Claude Code plugin system (`.claude-plugin/plugin.json` +
  marketplace) as the distribution mechanism — would give automatic command
  namespacing/collision-avoidance for free, but is a bigger structural change from
  the current zip+installer flow and wasn't pursued since the flat-file approach
  already meets the requirement. Worth reconsidering only if the number of shipped
  commands grows a lot or the flat-namespace assumption stops holding.
