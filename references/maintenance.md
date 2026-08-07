# Maintaining this skill

Only needed when revising the skill itself — not during a refinement session.

## Updating `paper-summaries.md` from new algorithm papers (PDFs)

If pointed at a folder of the journal-paper PDFs behind TOPAS's algorithms:

**PDF text extraction.** `Read`'s PDF-rendering path needs `pdftoppm` (poppler-utils); without it, `python -m pip install pypdf` and use `PdfReader(path).pages[i].extract_text()`. Plain-text extraction, no OCR/layout awareness — fine for prose, mangles typeset math objects (same limitation as the DOCX manual). Extract to a scratch directory, never into the skill.

**Don't assume filenames map 1:1 to papers.** Check title/author/abstract of every file — a folder can hold a non-paper (a conference certificate), a pre-typesetting draft alongside the published version under a different name, or exact duplicates.

**A paper's own header is the authoritative citation, and can catch existing errors.** IUCr/Acta Cryst reprints print the real `J. Appl. Cryst. (YYYY). VOL, PAGES` on the cover and in the header. Re-derive citations from the source rather than trusting `paper-summaries.md`.

**Carry the paper's concrete numbers, not just its abstract-level claim** — default parameter values, correlation/accuracy caveats and worked-example numbers are exactly what someone debugging an `.inp` needs. Worth a second pass even when a first-pass summary isn't wrong, just shallow.

## Updating the references from a revised Technical Reference (DOCX or PDF)

These files were built from *TOPAS-Academic Technical Reference* (Alan Coelho), cross-checked against a PDF export and the source `.docx`.

**Get the file open correctly.** For a large `.docx`, pull just `word/document.xml` (`unzip -p file.docx word/document.xml > document.xml`); unpack fully only to edit and repackage. Parse with `lxml.etree` and the WordprocessingML namespace, not regex — a naive regex against raw OOXML silently leaks XML into extracted text at a self-closing `<w:t/>`.

**Re-resolve chapter/section numbers by heading text, not an assumed running number** — numbering drifts between editions (one duplicated heading shifts everything after it). Walk `Heading1`–`Heading4` and match actual text. This skill's `00`–`27` filename prefixes are an independent scheme and don't track the manual's chapters.

**Keywords are marked by a Word character style, not just a color.** `AacKeyword1` (orange italic) and `AacKeywordHyperLink` (blue bold-italic, ~7% of keyword mentions) are both real; a color-only scan misses the second. Macros use `AacMacro`, reserved parameters `AacReservedParameters`, filenames `AacFile`. Trap: a run can carry `AacKeyword1` with an explicit `<w:color w:val="auto"/>` override, rendering as ordinary black — leftover formatting, not a keyword; filter these out.

**Keyword-dependency hierarchy hides behind two indentation mechanisms**: paragraph-level `w:ind`/`@left` (twips — ~357–360 ≈ one level, ~714–720 ≈ two, ~1068–1074 ≈ three), or literal leading `<w:tab/>` elements with no `w:ind`. Check both per paragraph. A bare `T`-prefixed name (`Ttop`, `Tcomm_2`) starts a new type's definition; the same name appearing as a member elsewhere is a mixin ("insert everything that type defines here too"), not a nested child, unless it genuinely has further bracketed keywords. Check real indent values before assuming a flat list needs rebuilding, and don't mistake ordinary code-example indentation for hierarchy.

**Verify any suspected content difference or typo two independent ways** (DOCX vs. an independent PDF extraction) before reporting it as a manual error rather than an extraction artifact. Confirmed real findings already fixed here: `out_dependents_for` → `out_dependences_for`, missing/doubled parentheses in worked examples, `ATMSCAT.CPP` → `ATMSCAT.TXT`. Conversely, don't "fix" deliberate conventions — `...` meaning "content omitted" is not broken code.

**`check_inp_syntax.py` runs at scale across extracted snippets but expect real false positives** from the `...` convention, non-INP content with brackets/parens (results tables, space-group symbols), and English words resembling keywords. Hand-verify every flag against the source.

**This environment has occasionally reverted a file to an earlier state between turns** — after a long edit chain, spot-check that earlier fixes are still present before declaring the update complete.

**The dominant failure mode found during full re-verification: a `##`/`###` heading kept its text but its body prose was silently dropped**, while surrounding tables/code survived — showing up as an empty subsection, a multi-branch list missing branches, or a keyword signature with no description. Grep each chapter's paragraph *count* against the source rather than only checking known strings; a dropped paragraph produces no error, just silence. Don't assume a past confirmed fix stayed fixed — one had regressed by a later pass.
