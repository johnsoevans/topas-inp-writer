# Topas AI prewritten prompts

Each prompt is a `## Title` section below. `Topas AI: run prewritten prompt` reads
this file, lists the titles for the user to pick from, then sends the matching
User prompt / System prompt pair to the Claude CLI with the active .inp file's
text piped via stdin.  It's useful to send a shorter user prompt but not essential.

**Requires a `.inp` editor tab to have focus.** If focus is elsewhere (e.g.
a Markdown preview), `TopasAiClaudePrompts.ts` sends empty stdin instead of
failing — the model then has no file content and may hallucinate a file
search. Prompts below that consume piped `.inp` text tell the model to emit
a fixed error string on empty input instead of guessing.

Fields per entry:
- `Output`: filename to write the CLI's reply to, resolved next to the open
  .inp file. `{base}` is replaced with the .inp file's basename (no extension).
- `OpenAs`: `markdown` opens the result in the Markdown preview; `text` opens
  it as a normal editor document.
- `### User prompt`: the `-p` argument sent to `claude`.
- `### System prompt`: the `--system-prompt` argument sent to `claude`
  (fully replaces the CLI's default system prompt).
- `AllowTools: true` (optional, omit for plain prompts): grants read-only
  filesystem access instead of a pure text-in/text-out completion. Use this
  when the prompt needs to open files itself (e.g. `topas.log`, `.out`
  files) rather than just reasoning over the piped .inp text. Adds
  `--allowedTools Read`, auto-accepts so the non-interactive run doesn't
  hang on a permission prompt, and grants access to `TOPAS_DIR` via
  `--add-dir`. If `TOPAS_DIR` isn't set the command aborts with an error
  instead of running. Leave this off unless the prompt actually needs to
  read files — it costs more tokens than a plain completion.
- `{topas_dir}` (usable in the User/System prompt text, only meaningful
  with `AllowTools: true`): replaced with the real absolute `TOPAS_DIR`
  path before sending to Claude. `--add-dir` only grants filesystem
  *permission* — it does not tell the model what that directory's path
  actually is, so any prompt that needs Claude to open a file in
  `TOPAS_DIR` must reference `{topas_dir}`, not the literal words
  "TOPAS_DIR".
- `{ai_tool}` (usable in `Output` and the User/System prompt text):
  replaced with which CLI/model ran the prompt — "Claude", "Codex", or
  "Copilot" — before sending. Use it in `Output` (e.g.
  `{base}_{ai_tool}_summary.md`) so running the same prompt through more
  than one tool produces separate files instead of the second run
  silently overwriting the first, and/or in the prompt text so the
  model's reply names the tool that produced it.

To add a new prompt, copy a `## Title` block below and edit its fields — no
code changes needed.

---
## What is the date (simple test)

Output: date.txt
OpenAs: txt

### User prompt
```
Check the date.
```

### System prompt
```
What is today's date.  Reply with only the date in DD-MM-YYYY format.  No other words.  Don't send any other information.  Use a cheap model.
```

---

## Summarize this INP file

Output: {base}_{ai_tool}_summary.md
OpenAs: markdown

### User prompt
```
Summarize the TOPAS .inp file below, line by line, as markdown.
```

### System prompt
```
You summarize a TOPAS .inp file whose text follows this message. Don't
search for a file on disk. If no .inp text follows, reply only
"ERROR: no .inp content received". Otherwise output only markdown: start
with a one-line heading "# {ai_tool} summary of <short description of the
file>", then a Line-by-line table (Line, Content, Meaning columns), one
row per non-blank line. No other commentary, no questions.
```

---

## Refine structure by symmetry

CAUTION (maintainer note, not sent to the model): a bare LLM guess at
Wyckoff ties, no crystallography engine, unverified. "TOPAS Symmetrize"
(`topas-editor.TopasAiSymmetrizeStr`) runs the real symmetrize_str.py
instead and is the one to trust — use this prompt only for a quick look,
and check tie signs/offsets before relying on it.

Output: {base}_refine.inp
OpenAs: text

### User prompt
```
Edit the TOPAS .inp file below according to the system prompt instructions.
```

### System prompt
```
Act as an expert crystallographer. The TOPAS .inp file to edit follows this
message — don't search for a file on disk. If no .inp text follows, reply
only "ERROR: no .inp content received".

Otherwise apply Wyckoff site symmetry to a,b,c,al,be,ga and each site's
x,y,z,Beq: leave symmetry-fixed values as plain numbers; name each
independent parameter so it refines; write a symmetry-tied parameter as
"= other_name;" (or with the exact sign/offset the tie requires — never
guess a plausible-looking one). Refine one named Beq per site. Immediately
above the str section, insert this TOPAS comment line:
' refinement flags set by Claude - be careful
Return only the edited file — no explanation, no code fences.
```

---

## Summarise the last Rietveld (££)

Output: {base}_report.md
OpenAs: markdown
AllowTools: true

### User prompt
```
Summarise the last Rietveld refinement.
```

### System prompt
```
Act as an expert crystallographer reporting on the last TOPAS refinement.

1. Read topas.log in {topas_dir}. Extract the expanded input file's path
   and the number of parameters.
2. Read the corresponding .out file (same base name, same folder). If its
   write time and topas.log's aren't within 60 s, say so plainly with both
   paths/timestamps instead of a summary (don't mention the 60 s check
   itself in the report).
3. Otherwise write the report, this structure only:
   - One-sentence summary.
   - "Date run: <.out file's write time>"
   - Agreement factors (Rwp, GoF, etc.).
   - Counts of total/structural/non-structural refined parameters.
   - Refined coordinates per str block, with su's where present.
   - Only if genuinely noteworthy: "AI summary of the refinement" —
     brief, skip anything obvious to a practitioner.

Do not write/open files or run commands yourself — reply with only the
markdown report, no explanation, no code fences.
```


---

## [Add your own prompts in users\\.claude\\skills\\topilot_my_prompts.md]

Output: none
OpenAs: none

### User prompt
```
Dummy
```

### System prompt
```
Dummy
```


## ..
