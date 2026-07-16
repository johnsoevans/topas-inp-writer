# The Log File (tc.log): Macro Expansion and Real LINE Numbering

Every time `tc.exe` runs, it writes a log file (`tc.log` by default, next to the executable/working directory) containing the INP file **after all macros, `#include`s, and preprocessor directives have been expanded** — this is the literal text actually fed to the TOPAS kernel, not the file as the user wrote it. When TOPAS reports an error "at LINE N", N is a line number in this expanded form, not necessarily the line number you'd get counting lines in the original `.inp` in a text editor.

This file documents the exact expansion rules, confirmed by diffing real `tc.log` output (captured by concatenating many runs into one file, each run delimited by `*** Start of expanded input file: <path> ***` / `*** End of expanded input file: <path> ***`) against the original bundled `.inp` files.

## Confirmed line-numbering rules

Comparing `references/examples/cf/alvo4a.inp` and `references/examples/pdf/pdf-1.inp` against their real expanded log output line-by-line establishes these rules precisely:

1. **A line comment (`'...` to end of line) becomes one blank line.** 1:1, unsurprising since it was already a single line.
2. **A block comment (`/* ... */`), however many physical lines it spans, collapses to exactly ONE blank line in the expanded output — never one line per physical line of the comment.** A 7-line `/* ... */` block becomes 1 blank line, shifting every subsequent line number up by (span - 1). This is the mechanism behind an apparent mismatch between a text editor's line count and TOPAS's own "at LINE N": count physical lines, then subtract (comment span − 1) for every block comment above the reported location, and note that TOPAS's own numbering will fall further "behind" the raw file after each block comment. It was originally confirmed by working backward from a real error (`sites_geometry_1.inp`'s `at LINE 9` for `ycalc_out`, whose physical line is 15 — a 7-line block comment earlier in the file accounts for exactly the 6-line discrepancy); it is now directly confirmed by inspecting real expanded log content.
3. **A `macro Name(...) { ... }` *definition* itself contributes exactly one blank output line, regardless of how many lines the macro body spans**, since the definition itself produces no runtime content — only *invocations* of the macro expand inline (see below).
4. **`#ifdef NAME` / `#ifndef NAME` and the matching `#endif` directive lines each individually collapse to one blank output line** — same treatment as a comment line.
5. **The entire untaken branch of an `#ifdef`/`#ifndef`/`#else` is deleted from the output with NO placeholder lines at all** — not even one. This is different from a block comment (which always gets exactly 1 placeholder line) and different from the bounding directives themselves (which each get exactly 1). Concretely, for
   ```
   #ifdef CREATE_
      iters 0
      yobs_eqn !aac.xy = 1;
         ...
   #else
      xdd pdf-1.xy
   #endif
   ```
   with `CREATE_` never `#define`d: the `#ifdef CREATE_` line and the `#endif` line each become one blank line, but everything from directly after `#ifdef CREATE_` through and including the `#else` line vanishes completely — contributing zero lines — while the taken branch's own content (`xdd pdf-1.xy`) appears as normal, unmodified content. Verified exactly against `references/examples/pdf/pdf-1.inp` line-by-line.
6. **A runtime `if cond { ... } else { ... }` (lowercase `if`, a real TOPAS keyword, not the `#if` preprocessor directive) is NOT pruned — both branches appear intact in the expanded log**, because the condition can itself be a parameter/equation evaluated at refinement time, not a compile-time constant the way `#ifdef`'s argument is. Verified against `references/examples/cf/alvo4a.inp`'s `if 0 { ... xdd \c\t5\cf\alvo4-sim.xy } else { xdd alvo4.xdd ... }` — both the `if 0 {` and `} else {` lines and both bodies survive expansion unchanged, line-for-line, with only the comments inside each branch collapsing per rules 1-2 above.

**Practical implication for debugging:** files that hit a genuine parse-time error (`*** Error loading sstring_in ... at LINE N`) did not produce a `*** Start of expanded input file ***` entry at all in the batch log used to derive these rules — consistent with the error occurring *during* expansion, before the kernel ever received a complete expanded file. If you're trying to match a `LINE N` from this class of error against your source, apply rules 1-6 by hand from the top of the file down to the reported line; there is no completed `tc.log` to compare against for a file that failed to parse.

`scripts/check_inp_syntax.py` (see `SKILL.md`) intentionally reports plain physical line numbers, not this expanded numbering — use it to find the right neighborhood, then apply the rules above if you need to match TOPAS's own reported number exactly.

## Macro argument substitution mechanics

Diffing macro *invocations* against their expanded form shows two consistent substitution behaviors:

**Plain arguments are wrapped in parentheses at every point of use.** A macro parameter substituted with a literal value shows that value parenthesized in the expansion, e.g. `LP_Factor(17)` (a macro taking a two-theta-of-monochromator argument) expands to:
```
scale_pks = (1 + Cos((17) 0.01745329251994)^2 Cos(2 Th)^2) / (Sin(Th)^2 Cos(Th));
```
— the substituted `17` appears as `(17)`, not bare `17`, preserving operator precedence regardless of what expression was actually passed in. Expect this parenthesization anywhere a macro argument is used inside an equation in the expanded log/errors; it is not a typo or a doubled value.

**`@`-flagged arguments (anonymous refined parameters) are replaced with an auto-generated internal name of the form `m<8-hex-like-chars>_<index>`.** The hash-like prefix is shared across the whole file; the numeric suffix increments once per `@`-argument encountered during expansion, in source order. For example, `Simple_Axial_Model(@, 11.21014\`_0.07193)` followed later by `Zero_Error(@, -0.02897\`_0.00046)` in the same file expand to:
```
prm m6a4bb722_0 11.21014`_0.07193 min 0.0001 max 50  circles_conv = -.5 57.2957795130823 ( (m6a4bb722_0) / Rs)^2 / Tan(2 Th);
prm m6a4bb722_1 -0.02897`_0.00046 min = ...;  ...  th2_offset = (m6a4bb722_1);
```
Both the declaration and every later reference within that macro's body use the identical generated name (`m6a4bb722_0`, `m6a4bb722_1`, ...), each individually parenthesized per the rule above. This is the actual internal identity behind an `@`-anonymous parameter — when an error mentions a name matching this `m<hash>_<n>` pattern, it's referring to a specific auto-named `@` parameter, not a corrupted or foreign name; trace it back to the `@` argument at the matching position in the source.

## Confirmed exact expansions of common built-in macros

These come directly from `topas.inc` (the default macro library) and were confirmed by diffing real invocations against their expanded form:

- `STR(space_group, phase_name)` -> `str space_group <space_group> phase_name <phase_name>`
- `XDD(name)` -> `xdd <name>.xdd` (appends the `.xdd` extension automatically)
- `LP_Factor(tth)` -> `scale_pks = (1 + Cos(<tth> 0.01745329251994)^2 Cos(2 Th)^2) / (Sin(Th)^2 Cos(Th));` (the constant is Pi/180, i.e. degrees-to-radians)
- `PV_Peak_Type(..., lor_coeffs..., fwhm_coeffs..., ...)` -> `peak_type pv pv_lor = <a> + <b> Tan(Th) + <c> / Cos(Th); pv_fwhm = <d> + <e> Tan(Th) + <f> / Cos(Th);` (a Cagliotti-style construction matching `references/04-peak-generation-and-peak-type.md`'s description of the PV peak type)

## Batch log format (multi-run concatenation)

When many runs' `tc.log` output is concatenated into one file (as in a batch script that doesn't clear the log between runs), each run's content is delimited by:
```
*** Start of expanded input file: c:\path\to\file.inp ***
...expanded content...
*** End of expanded input file: c:\path\to\file.inp ***
```
The same path can appear more than once if the batch re-ran that file (e.g. deliberately re-invoked, or a file using `num_runs`/`continue_after_convergence` that writes more than one expansion pass) — don't assume a path is unique within a concatenated log.
