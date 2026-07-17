#!/usr/bin/env python3
"""
param_dependency_trees.py -- Build two dependency trees for the refined
and computed parameters in a TOPAS .inp file:

  Tree 1 (--tree dependent, default): every DEPENDENT parameter/keyword
    (one whose value is computed via an equation referencing other
    parameters) as a root, with the parameters/keywords it references as
    children -- recursed until reaching independent (refined) or fixed
    leaves.
  Tree 2 (--tree independent): every INDEPENDENT (refined) parameter as
    a root, with the dependent parameters/keywords that reference it
    (directly, and transitively through further dependents) as children.

A bare '@'-flagged keyword value (e.g. `beq @ 1.34160`, `a @ 10.820399`)
has no name of its own -- per the request this was built for, it's
labeled with its KEYWORD instead (e.g. "beq", "a").

Method: fully macro-expands the file first (via expand_inp_macros.py),
then scans the expanded, comment-stripped text for every equation
('KEYWORD [sigil][name]? = expr;') across two contexts:
  1. `prm`/`local` -- ALL of them, including '!'-prefixed ones (unlike
     find_refined_params.py, which is only interested in independently
     REFINED parameters and so skips '!'-prefixed equations outright;
     this script needs the full computation graph regardless of whether
     a node is itself further refined).
  2. A curated set of other keywords confirmed to carry a bare value OR
     an equation directly (KEYWORD_EQ_LIST below: site x/y/z/occ/beq/
     u11..u23, lattice a/b/c/al/be/ga/scale, rotate/translate, and the
     rigid-body Z-matrix's own ta/tb/tc bond/angle/torsion assignment
     keywords) -- deliberately NOT every possible TOPAS keyword; see
     "Known limitations" below.

`local` re-scoping: the SAME name declared in multiple `local` statements
(e.g. a per-pressure-point block repeated 7 times in the file this was
built for) is genuinely a DIFFERENT parameter each time -- never
deduplicated, matching find_refined_params.py's own established rule.
Each repeated local declaration is disambiguated by its own 1-based
occurrence index (e.g. "Pb_a #3"). A reference to that name from within
an equation is resolved to the NEAREST PRECEDING declaration of it (by
line number) -- a "most recent definition wins" scoping heuristic that
matches this file's real structure (each pressure-point block computes
its own Pressure/V/b1 chain from its own Pb_a before the next block's
Pb_a appears), not a general TOPAS scoping rule.

A rigid body's `z_matrix { ... }` block gets its own dedicated row parser
(parse_z_matrix_row_nodes) rather than being scanned by the general
keyword-equation grammar above: each row (e.g. `O1  C1 =do1c1;  C2
=ao1c1c2;  N1 =torco2;`) defines up to three equations for one atom --
bond distance, bond angle, then torsion angle, in that column order
(confirmed by the variable-naming convention used throughout the worked
examples: do1c1 = distance O1-C1, ao1c1c2 = angle O1-C1-C2). The row's
own leading atom label and every reference-atom label before an '='
(O1, C1, C2, N1 above) are internal z-matrix atom tags, not TOPAS
parameters -- only the expression after each '=' is a real equation,
shown as a synthetic dependent node labeled e.g. "O1 (z_matrix bond)".
This was added after a direct, real discrepancy check against TOPAS's
own `out_dependences_for` keyword (run on a rigid body tagged
`out_dependences_for aaa rigid` in
test_examples/sp/serine_i_evans_n_ta_bang_rot-z.inp): TOPAS's real
dependency list included dc1c2, an1c2c1, do1c1, ao1c1c2, toroh_0/1/2,
and 30+ other z-matrix-row-only references that this script previously
showed as isolated independent roots with zero "referenced by" children,
because the entire z_matrix span was excluded outright rather than
parsed. Note TOPAS's own out_dependences_for additionally filters to
only parameters that carry real refinement uncertainty (skipping a
purely-`!`-fixed, never-refined chain like torco2_0/1/2 entirely) --
this script does NOT apply that filter, by design (see the module intro
above: it shows the FULL computation graph regardless of refined
status), so its z-matrix-row output is a superset of what
out_dependences_for reports, not a literal match line-for-line.

Known limitations, stated plainly:
  - KEYWORD_EQ_LIST is curated, not exhaustive -- a keyword/equation
    outside it is simply not discovered as its own node (though if
    something else's equation references its name and that name is
    independently found via find_refined_params.py's own scan, it still
    appears correctly as a leaf).
  - Reference extraction only trusts an identifier as a real reference if
    it matches a name/keyword this script ALSO found declared somewhere
    (an "allowlist" approach) -- this avoids needing to enumerate every
    TOPAS built-in function/reserved word (Cos, Get, Th, X, Yobs, ...) by
    hand, but means a genuine reference to a parameter this script failed
    to discover (e.g. one declared via a KEYWORD_EQ_LIST gap above) is
    silently dropped rather than shown as an unresolved reference.

Usage:
    python3 param_dependency_trees.py file.inp
    python3 param_dependency_trees.py file.inp --tree independent
    python3 param_dependency_trees.py file.inp -o report.txt
    python3 param_dependency_trees.py file.inp -o report.txt --no-open
    python3 param_dependency_trees.py file.inp -o report.html

After writing the report (default in-place stdout redirect via -o, not
plain stdout), it also opens/focuses that file in VS Code -- matching
format_inp_hierarchy.py's own established convention -- via
shutil.which("code")/"code.cmd" (a bare "code" often isn't found by
subprocess's own PATH search on Windows, unlike a real shell). Pass
--no-open to skip this, or omit -o (plain stdout) to skip it automatically.

**`-o` with a `.html`/`.htm` extension renders an interactive page
instead** of the plain-text report -- both trees as click-to-expand/
collapse node lists (tabbed, not side by side, since either tree alone
can be very large -- 251 dependent roots / 158 independent roots on the
serine file this script was built for), color-coded by kind
(independent/dependent/fixed), plus a live search box that auto-expands
every ancestor of a match. Self-contained, no CDN dependencies, dark/
light via `prefers-color-scheme` -- matching this skill's established
visualization pattern (see `topas_keyword_tree.py`/`plot_xy.py`). Opens
in the default web browser afterward, NOT VS Code -- this script is the
one place in the skill that can emit either a text report or an HTML
page from the same `-o` flag, so the open-target follows the actual
output format rather than being fixed to one convention.
"""

import sys
import os
import re
import json
import shutil
import subprocess
import argparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import check_inp_syntax as cis
from expand_inp_macros import expand_file
import find_refined_params as frp

NAME_TOK_RE = re.compile(r"(?:([!@])?([A-Za-z_]\w*))|([!@])")
NUMBER_RE = cis.E_ARG_NUMBER_TOKEN_RE
IDENT_RE = re.compile(r"[A-Za-z_]\w*")

# Bare keywords (outside prm/local) confirmed in real usage to carry
# either a bare/'@' value or a '= expr;' equation directly -- see the
# module docstring for why this is curated, not exhaustive.
KEYWORD_EQ_LIST = (
    "x", "y", "z", "occ", "beq",
    "u11", "u22", "u33", "u12", "u13", "u23",
    "a", "b", "c", "al", "be", "ga", "scale",
    "rotate", "translate", "ta", "tb", "tc",
)

Z_MATRIX_KW_RE = re.compile(r"\bz_matrix\b")


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def find_z_matrix_spans(text):
    """Brace-matched spans of every 'z_matrix { ... }' block, excluded
    from the keyword-equation scan -- see module docstring."""
    spans = []
    for m in Z_MATRIX_KW_RE.finditer(text):
        pos = m.end()
        n = len(text)
        while pos < n and text[pos] in " \t\r\n":
            pos += 1
        if pos < n and text[pos] == "{":
            end = None
            depth = 0
            i = pos
            while i < n:
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
                i += 1
            if end:
                spans.append((m.start(), end))
    return spans


def _in_any_span(pos, spans):
    return any(s <= pos < e for s, e in spans)


class Node:
    def __init__(self, node_id, display, kind, line, expr=None, fixed=False, scoped=False):
        self.node_id = node_id       # unique key, e.g. "b1#3" for the 3rd 'local b1'
        self.display = display       # human label, e.g. "b1" or "beq (site D1)"
        self.kind = kind             # 'independent' | 'dependent' | 'fixed_constant'
        self.line = line
        self.expr = expr             # raw equation text, dependent nodes only
        self.fixed = fixed           # True if '!'-prefixed (not itself further refined)
        self.scoped = scoped         # True if this node does NOT have a single name shared
                                      # across the whole file -- 'local' (re-scoped per xdd/
                                      # phase) and anonymous '@'/positional-ADP forms both
                                      # qualify, and both get a genuinely fresh instance per
                                      # for-loop iteration if declared inside one. False for
                                      # a bare NAMED 'prm' or other bare-named keyword value --
                                      # TOPAS's kernel-enforced 'same name = same value' rule
                                      # keeps those as ONE shared parameter across every
                                      # for-loop iteration. Both halves of this rule were
                                      # confirmed empirically, not assumed -- see
                                      # find_refined_params.loop_multiplier()'s own docstring.
        self.refs = []                # node_ids this node's equation references (dependent only)


def parse_all_prm_local(clean_text):
    """Like find_refined_params.parse_prm_local_statements, but keeps
    EVERY prm/local (including '!'-prefixed ones) since this script needs
    the full computation graph, not just independently-refined parameters.
    Returns a list of Node objects plus the list of (start, end) spans
    each statement occupies (to exclude from the keyword-equation scan)."""
    nodes = []
    spans = []
    n = len(clean_text)
    occurrence_count = {}
    for m in frp.PRM_LOCAL_RE.finditer(clean_text):
        scoped = m.group(1) == "local"
        pos = m.end()
        while pos < n and clean_text[pos] in " \t\r\n":
            pos += 1
        if pos < n and clean_text[pos] == "=":
            # unnamed equation, e.g. 'prm = 2 a1^2 + 3;' -- has no name to
            # reference elsewhere, so not a useful graph node; skip.
            end = clean_text.find(";", pos)
            if end != -1:
                spans.append((m.start(), end + 1))
            continue

        tok_m = NAME_TOK_RE.match(clean_text, pos)
        if not tok_m or not tok_m.group(0):
            continue
        sigil = tok_m.group(1) or tok_m.group(3) or ""
        name = tok_m.group(2)
        if not name:
            continue
        k = tok_m.end()
        while k < n and clean_text[k] in " \t\r\n":
            k += 1

        line = line_of(clean_text, m.start())
        occurrence_count[name] = occurrence_count.get(name, 0) + 1
        occ = occurrence_count[name]
        node_id = f"{name}#{occ}" if scoped else name

        if k < n and clean_text[k] == "=":
            end = clean_text.find(";", k)
            if end == -1:
                continue
            expr = clean_text[k + 1:end].strip()
            spans.append((m.start(), end + 1))
            plain = cis.parse_plain_numeric_equation(expr)
            if plain is not None:
                nodes.append(Node(node_id, name, "independent", line, fixed=(sigil == "!"), scoped=scoped))
            else:
                node = Node(node_id, name, "dependent", line, expr=expr, fixed=(sigil == "!"), scoped=scoped)
                nodes.append(node)
            continue

        val_m = NUMBER_RE.match(clean_text[k:])
        if not val_m or not val_m.group(0):
            continue
        end = k + val_m.end()
        spans.append((m.start(), end))
        if sigil == "!":
            nodes.append(Node(node_id, name, "fixed_constant", line, fixed=True, scoped=scoped))
        else:
            nodes.append(Node(node_id, name, "independent", line, scoped=scoped))
    return nodes, spans


def parse_keyword_equations(clean_text, exclude_spans):
    """General '= expr;' scanner for KEYWORD_EQ_LIST, outside prm/local
    and z_matrix spans. Handles both 'KEYWORD = expr;' (e.g. 'beq =
    b1;') and 'KEYWORD NAME = expr;' -- neither has its own separate
    node identity issue like local, since none of these keywords are
    re-scoped the way local is (site keywords are inherently per-site
    already via their surrounding site statement, tracked here only by
    line/position, not deduplicated by keyword name alone)."""
    nodes = []
    n = len(clean_text)
    for kw in KEYWORD_EQ_LIST:
        for m in re.finditer(r"\b" + re.escape(kw) + r"\b", clean_text):
            if _in_any_span(m.start(), exclude_spans):
                continue
            pos = m.end()
            while pos < n and clean_text[pos] in " \t\r\n":
                pos += 1
            # optional name token before '='
            save_pos = pos
            name = None
            tok_m = NAME_TOK_RE.match(clean_text, pos)
            if tok_m and tok_m.group(0) and tok_m.group(2):
                k = tok_m.end()
                while k < n and clean_text[k] in " \t\r\n":
                    k += 1
                if k < n and clean_text[k] == "=":
                    name = tok_m.group(2)
                    pos = k
            if pos < n and clean_text[pos] == "=":
                end = clean_text.find(";", pos)
                if end == -1:
                    continue
                expr = clean_text[pos + 1:end].strip()
                line = line_of(clean_text, m.start())
                label = f"{kw}={name}" if name else f"{kw}@L{line}"
                plain = cis.parse_plain_numeric_equation(expr)
                display = name or kw
                if plain is not None:
                    nodes.append(Node(label, display, "independent", line))
                else:
                    nodes.append(Node(label, display, "dependent", line, expr=expr))
            else:
                pos = save_pos
    return nodes


Z_MATRIX_ROW_TOKEN_RE = re.compile(r"([A-Za-z_]\w*)(?:\s*(=)\s*([^;]+);)?")
Z_MATRIX_ROLES = ("z_matrix bond", "z_matrix angle", "z_matrix torsion")


def parse_z_matrix_row_nodes(clean_text, z_matrix_spans):
    """Each z_matrix row (e.g. 'O1  C1 =do1c1;  C2 =ao1c1c2;  N1
    =torco2;') defines up to three equations for one atom -- bond
    distance, bond angle, then torsion angle, in that column order. The
    row's own leading atom label and every reference-atom label before
    an '=' are internal z-matrix atom tags, not TOPAS parameters -- only
    the expression after each '=' is a real equation. See the module
    docstring for why this exists (a confirmed gap found by comparing
    against TOPAS's own out_dependences_for output).

    Reuses the OUTER z_matrix spans from find_z_matrix_spans() directly
    (rather than needing a separate inner-brace span) -- the leading
    'z_matrix' keyword token and the bare '{'/'}' braces harmlessly
    become an inert "current atom" that never accumulates any equations,
    since the very next real row (e.g. the first atom, which has no
    reference atoms of its own) immediately resets it."""
    nodes = []
    for start, end in z_matrix_spans:
        segment = clean_text[start:end]
        current_atom = None
        eq_index = 0
        for m in Z_MATRIX_ROW_TOKEN_RE.finditer(segment):
            ident = m.group(1)
            if m.group(2) is None:
                current_atom = ident
                eq_index = 0
                continue
            if current_atom is None:
                continue
            expr = m.group(3).strip()
            role = Z_MATRIX_ROLES[eq_index] if eq_index < len(Z_MATRIX_ROLES) else f"z_matrix ref{eq_index + 1}"
            eq_index += 1
            line = line_of(clean_text, start + m.start())
            label = f"{current_atom}#{role}@L{line}"
            display = f"{current_atom} ({role})"
            plain = cis.parse_plain_numeric_equation(expr)
            if plain is not None:
                nodes.append(Node(label, display, "independent", line))
            else:
                nodes.append(Node(label, display, "dependent", line, expr=expr))
    return nodes


def parse_inline_z_matrix_rows(clean_text, exclude_spans):
    """TOPAS has a SECOND z_matrix syntax, distinct from the 'load
    z_matrix { ... }' block form parse_z_matrix_row_nodes() handles: one
    'z_matrix ATOM [REF (=EXPR;|NUMBER)]*' statement per line, e.g.
    'z_matrix C1 X1 =rcc/2; X2 90' -- confirmed in
    test_examples/rigida-1.inp, where this script previously missed that
    C1's and C2's bond distances reference rcc directly (via '=rcc/2;')
    and C4's references rcc2 (itself '=rcc;'), because 'z_matrix' isn't
    in KEYWORD_EQ_LIST and this line form was never matched by
    find_z_matrix_spans() either (that function only recognizes the '{
    ... }' block form, so these lines weren't even excluded, let alone
    parsed -- out_dependences rcc on this exact file was the real,
    confirmed discrepancy that surfaced the gap).

    Each REF/value pair advances the same bond/angle/torsion role order
    as the block form; only '=EXPR;' pairs produce a real equation node
    -- a bare numeric value (e.g. 'X2 90') doesn't reference anything
    and is simply consumed and skipped, still advancing the role index
    so a later '=EXPR;' pair on the same row gets the right role.

    Each inline statement is bounded to its own physical line (matching
    the one-row-per-line convention used throughout this skill's INP
    files) rather than scanning to the next 'z_matrix' keyword -- safer
    than assuming statements are always back-to-back, at the cost of
    not handling a z_matrix row deliberately wrapped across lines
    (not observed in any example file)."""
    nodes = []
    n = len(clean_text)
    for m in Z_MATRIX_KW_RE.finditer(clean_text):
        pos = m.end()
        look = pos
        while look < n and clean_text[look] in " \t":
            look += 1
        if look < n and clean_text[look] == "{":
            continue  # block form, handled by parse_z_matrix_row_nodes
        if _in_any_span(m.start(), exclude_spans):
            continue

        eol = clean_text.find("\n", pos)
        if eol == -1:
            eol = n
        line_text = clean_text[pos:eol]
        line_no = line_of(clean_text, m.start())

        atom_m = IDENT_RE.match(line_text.lstrip(" \t"))
        if not atom_m:
            continue
        p = (len(line_text) - len(line_text.lstrip(" \t"))) + atom_m.end()
        atom = atom_m.group(0)
        role_index = 0
        ll = len(line_text)
        while p < ll:
            while p < ll and line_text[p] in " \t":
                p += 1
            ref_m = IDENT_RE.match(line_text, p)
            if not ref_m:
                break
            p = ref_m.end()
            while p < ll and line_text[p] in " \t":
                p += 1
            if p < ll and line_text[p] == "=":
                end = line_text.find(";", p)
                if end == -1:
                    break
                expr = line_text[p + 1:end].strip()
                role = Z_MATRIX_ROLES[role_index] if role_index < len(Z_MATRIX_ROLES) else f"z_matrix ref{role_index + 1}"
                label = f"{atom}#{role}@L{line_no}"
                display = f"{atom} ({role})"
                plain = cis.parse_plain_numeric_equation(expr)
                if plain is not None:
                    nodes.append(Node(label, display, "independent", line_no))
                else:
                    nodes.append(Node(label, display, "dependent", line_no, expr=expr))
                p = end + 1
                role_index += 1
            else:
                val_m = NUMBER_RE.match(line_text, p)
                if val_m and val_m.group(0):
                    p = val_m.end()
                    role_index += 1
                else:
                    break  # unrecognized token -- stop parsing this row defensively
    return nodes


def collect_independent_from_frp(clean_text, prm_local_spans):
    """Reuses find_refined_params.py's own non-prm/local independent-
    parameter finders (direct '@' keywords -- now including site x/y/z,
    beq/ADP components, mlx/mly/mlz, Flack, rigid-body transform
    keywords; ADP load blocks; Pawley/hkl_Is intensity load blocks; occ
    values; other named keyword values) so this script's leaf set matches
    that script's definition of 'independent' exactly -- one source of
    truth, not a second, potentially-drifting reimplementation."""
    nodes = []
    direct_at = frp.parse_direct_at_keywords(clean_text, prm_local_spans)
    for p in direct_at:
        label = p["keyword"]
        nodes.append(Node(label, label, "independent", p["line"], scoped=True))
    adp_loads = frp.parse_adp_load_blocks(clean_text, prm_local_spans)
    for p in adp_loads:
        # multiple ADP sites share keyword names (u11, u22, ...) -- keep
        # each occurrence distinct by line, like local's #occurrence.
        label = f"{p['keyword']}@L{p['line']}"
        nodes.append(Node(label, p["keyword"], "independent", p["line"], scoped=True))
    hkl_i_loads = frp.parse_hkl_intensity_load_blocks(clean_text, prm_local_spans)
    for p in hkl_i_loads:
        label = f"{p['keyword']}@L{p['line']}"
        nodes.append(Node(label, p["keyword"], "independent", p["line"], scoped=True))
    occ_values = frp.parse_occ_values(clean_text, prm_local_spans)
    for p in occ_values:
        if p["name"]:
            nodes.append(Node(p["name"], p["name"], "independent", p["line"]))
        else:
            label = f"occ@L{p['line']}"
            nodes.append(Node(label, "occ", "independent", p["line"], scoped=True))
    named_direct = frp.parse_named_keyword_values(clean_text, prm_local_spans)
    for p in named_direct:
        nodes.append(Node(p["name"], p["name"], "independent", p["line"]))
    return nodes


REF_GET_RE = re.compile(r"\bGet\s*\(\s*([A-Za-z_]\w*)\s*\)")


def extract_references(expr, known_display_names):
    """Identifiers in `expr` that match a known declared name/keyword
    display name (the 'allowlist' approach -- see module docstring)."""
    found = set()
    for gm in REF_GET_RE.finditer(expr):
        if gm.group(1) in known_display_names:
            found.add(gm.group(1))
    for im in IDENT_RE.finditer(expr):
        w = im.group(0)
        if w in known_display_names:
            found.add(w)
    return found


def resolve_reference(display_name, by_display_name, ref_line):
    """Nearest-preceding-declaration scoping for a reference to
    `display_name` seen at `ref_line` -- see module docstring."""
    candidates = by_display_name.get(display_name, [])
    if not candidates:
        return None
    best = None
    for node in candidates:
        if node.line <= ref_line:
            if best is None or node.line > best.line:
                best = node
    if best is None:
        best = min(candidates, key=lambda nd: nd.line)
    return best


def build_graph(inp_file, run_number=0):
    expanded, warnings = expand_file(inp_file, run_number=run_number)
    clean = cis.strip_comments_and_strings(expanded)

    z_matrix_spans = find_z_matrix_spans(clean)

    prm_local_nodes, prm_local_spans = parse_all_prm_local(clean)
    kw_eq_nodes = parse_keyword_equations(clean, prm_local_spans + z_matrix_spans)
    frp_independent_nodes = collect_independent_from_frp(clean, prm_local_spans)
    z_matrix_row_nodes = parse_z_matrix_row_nodes(clean, z_matrix_spans)
    z_matrix_inline_nodes = parse_inline_z_matrix_rows(clean, prm_local_spans + z_matrix_spans)

    all_nodes = {}
    by_display_name = {}
    for node in prm_local_nodes + kw_eq_nodes + frp_independent_nodes + z_matrix_row_nodes + z_matrix_inline_nodes:
        all_nodes[node.node_id] = node
        by_display_name.setdefault(node.display, []).append(node)
    for lst in by_display_name.values():
        lst.sort(key=lambda nd: nd.line)

    known_display_names = set(by_display_name.keys())

    for node in all_nodes.values():
        if node.kind != "dependent" or not node.expr:
            continue
        ref_names = extract_references(node.expr, known_display_names)
        ref_names.discard(node.display)  # no self-reference
        for rn in ref_names:
            target = resolve_reference(rn, by_display_name, node.line)
            if target is not None and target.node_id != node.node_id:
                node.refs.append(target.node_id)

    relabel_autonamed(all_nodes, clean)

    return all_nodes, warnings, clean


AUTONAME_RE = re.compile(r"^[mu][0-9a-f]{8}_\d+$")


def relabel_autonamed(all_nodes, clean_text):
    """A macro-internal auto-generated '@'-parameter name (e.g. from a
    peak-shape macro's own #m_argu handling, 'mb6d5dfaa_13') has no
    keyword of its own by the time it reaches this script -- macro
    expansion has already replaced the call with a plain 'prm HASHNAME
    value;' statement, discarding which macro argument it came from.
    Per the request this was built for ("when @ occurs, simply use the
    keyword associated with the parameter"), relabel it by finding the
    keyword that actually CONSUMES its value elsewhere in the file (e.g.
    'pv_fwhm = (mb6d5dfaa_13) ...;' -> label it 'pv_fwhm'), keeping the
    original hash name in parentheses for traceability/uniqueness. Purely
    cosmetic -- runs after all reference edges are already resolved by
    node_id, so it can't affect the graph itself, only how a node is
    displayed."""
    for node in all_nodes.values():
        if not AUTONAME_RE.match(node.display):
            continue
        m = re.search(r"\b([A-Za-z_]\w*)\s*=\s*\(?\s*" + re.escape(node.display) + r"\b", clean_text)
        if m and m.group(1) != node.display:
            node.display = f"{m.group(1)} ({node.display})"


def render_dependent_tree(all_nodes, out, max_depth=25):
    dependents = sorted(
        (n for n in all_nodes.values() if n.kind == "dependent"),
        key=lambda nd: (nd.line, nd.display),
    )
    rendered = set()
    for root in dependents:
        out.append(_format_root(root))
        if root.node_id in rendered:
            out.append("  (already shown above -- see its own entry)")
        else:
            rendered.add(root.node_id)
            _render_children(root, all_nodes, out, prefix="  ", visited={root.node_id}, depth=1, max_depth=max_depth, rendered=rendered)
        out.append("")


def render_independent_tree(all_nodes, out, max_depth=25):
    # reverse edges: independent/fixed node -> dependents that reference it
    reverse = {}
    for node in all_nodes.values():
        for ref_id in node.refs:
            reverse.setdefault(ref_id, []).append(node.node_id)

    roots = sorted(
        (n for n in all_nodes.values() if n.kind == "independent"),
        key=lambda nd: (nd.display, nd.line),
    )
    rendered = set()
    for root in roots:
        out.append(_format_root(root))
        if root.node_id in rendered:
            out.append("  (already shown above -- see its own entry)")
        else:
            rendered.add(root.node_id)
            _render_dependents(root, all_nodes, reverse, out, prefix="  ", visited={root.node_id}, depth=1, max_depth=max_depth, rendered=rendered)
        out.append("")


def _format_root(node):
    tag = _tag(node)
    return f"{node.display}{tag}  (line {node.line})"


def _tag(node):
    if node.kind == "independent":
        return " [independent, refined]" if not node.fixed else " [fixed]"
    if node.kind == "fixed_constant":
        return " [fixed]"
    exprbit = f"  = {node.expr}" if node.expr else ""
    fixedbit = " [!]" if node.fixed else ""
    return f" [dependent{fixedbit}]{exprbit}"


def _render_children(node, all_nodes, out, prefix, visited, depth, max_depth, rendered):
    """See _children_json's docstring for the full reasoning (a real,
    confirmed hang on a densely cross-referenced file, found via
    faulthandler.dump_traceback_later()). Mirrors that same "expand a
    shared node's subtree in full only the FIRST time, note '(already
    shown above)' every time after" fix for plain-text output -- an
    earlier attempt here only memoized and re-emitted the same cached
    LINES at every reuse, which fixed the CPU cost of re-walking the
    graph but not the output-size cost of re-printing a big shared
    subtree's text at every position it's referenced from; this fix
    bounds total output size by the number of distinct nodes, not by
    how many times they're referenced. `rendered` (global, not
    path-specific) tracks that; `visited` (path-specific) still decides
    cycle detection fresh on every call, unaffected by this."""
    if depth > max_depth:
        out.append(prefix + "... (max depth reached)")
        return
    if not node.refs:
        return
    for i, ref_id in enumerate(node.refs):
        child = all_nodes.get(ref_id)
        if child is None:
            out.append(prefix + f"- {ref_id} [unresolved reference]")
            continue
        last = i == len(node.refs) - 1
        branch = "`-- " if last else "|-- "
        cycle = child.node_id in visited
        already = (not cycle) and child.node_id in rendered
        note = "  (cycle, stopping)" if cycle else ("  (already shown above, see its own entry)" if already else "")
        out.append(prefix + branch + child.display + _tag(child) + f"  (line {child.line})" + note)
        if cycle or already:
            continue
        if child.kind == "dependent":
            rendered.add(child.node_id)
            new_prefix = prefix + ("    " if last else "|   ")
            _render_children(child, all_nodes, out, new_prefix, visited | {child.node_id}, depth + 1, max_depth, rendered)


def _render_dependents(node, all_nodes, reverse, out, prefix, visited, depth, max_depth, rendered):
    """See _render_children's docstring -- same "expand once" fix,
    mirrored for the reverse-edge (independent -> dependents) tree."""
    if depth > max_depth:
        out.append(prefix + "... (max depth reached)")
        return
    children_ids = reverse.get(node.node_id, [])
    for i, cid in enumerate(children_ids):
        child = all_nodes.get(cid)
        if child is None:
            continue
        last = i == len(children_ids) - 1
        branch = "`-- " if last else "|-- "
        cycle = child.node_id in visited
        already = (not cycle) and child.node_id in rendered
        note = "  (cycle, stopping)" if cycle else ("  (already shown above, see its own entry)" if already else "")
        out.append(prefix + branch + child.display + _tag(child) + f"  (line {child.line})" + note)
        if cycle or already:
            continue
        rendered.add(child.node_id)
        new_prefix = prefix + ("    " if last else "|   ")
        _render_dependents(child, all_nodes, reverse, out, new_prefix, visited | {child.node_id}, depth + 1, max_depth, rendered)


def _tag_kind(node):
    """Short machine-readable tag for JSON/HTML rendering -- the same
    four cases _tag() formats as text, kept as a distinct string so the
    page's CSS/JS can color-code without re-parsing prose."""
    if node.kind == "independent":
        return "fixed" if node.fixed else "independent"
    if node.kind == "fixed_constant":
        return "fixed"
    return "dependent_fixed" if node.fixed else "dependent"


def _node_json(node):
    return {
        "display": node.display,
        "tag": _tag_kind(node),
        "expr": node.expr if node.kind == "dependent" else None,
        "line": node.line,
        "cycle": False,
        "unresolved": False,
        "already_shown": False,
        "children": [],
    }


def _children_json(node, all_nodes, visited, depth, max_depth, rendered):
    """`rendered` is a set of node_ids already fully expanded ONCE,
    anywhere in this whole tree (not path-specific like `visited`).
    A node referenced from many places (extremely common: several
    equations all sharing one underlying parameter, e.g. the same
    physical constant used across many pressure points) is expanded
    in full only the FIRST time it's reached; every later reference to
    that same node_id is rendered as a compact "already_shown" pointer
    instead of re-embedding its whole subtree again.

    This fixes TWO distinct problems, found via faulthandler.
    dump_traceback_later() on a genuine, confirmed hang processing
    test_examples/sp/serine_i_evans_n_ta_bang_rot.inp (7 pressure
    points, heavy sharing of common parameters across all of them) --
    a file whose near-identical companion (...-z.inp) completed in
    seconds, during this skill's own curated-corpus regression sweep:
    (1) naive re-expansion is exponential in fan-out for a densely
    cross-referenced dependency DAG (the first fix attempted here only
    memoized the computed Python structure, which fixed the CPU-time
    blowup but not problem 2); (2) json.dumps() has no concept of a
    shared reference -- even a memoized, O(1)-to-reuse Python list still
    gets its full text written out again at EVERY position it's
    embedded, so the serialized output size (and json.dumps's own walk
    of it) is still unbounded by fan-out alone. Marking every repeat
    occurrence as a short pointer instead of a full re-embed bounds
    total output size by the number of DISTINCT nodes actually in the
    graph, not by how many times they're referenced.

    Whether descending into a child AT ALL is still decided fresh every
    time from the PATH-specific `visited` set (so an immediate cycle
    back to an ancestor on THIS path is always caught, distinct from
    `rendered`, which only tracks "already shown in full once" and has
    nothing to do with cycle detection)."""
    if depth > max_depth:
        return [{"display": "... (max depth reached)", "tag": "note", "expr": None,
                  "line": None, "cycle": False, "unresolved": False, "already_shown": False, "children": []}]
    result = []
    for ref_id in node.refs:
        child = all_nodes.get(ref_id)
        if child is None:
            result.append({"display": ref_id, "tag": "note", "expr": None, "line": None,
                            "cycle": False, "unresolved": True, "already_shown": False, "children": []})
            continue
        entry = _node_json(child)
        entry["cycle"] = child.node_id in visited
        if not entry["cycle"] and child.kind == "dependent":
            if child.node_id in rendered:
                entry["already_shown"] = True
            else:
                rendered.add(child.node_id)
                entry["children"] = _children_json(child, all_nodes, visited | {child.node_id}, depth + 1, max_depth, rendered)
        result.append(entry)
    return result


def build_dependent_tree_json(all_nodes, max_depth=25):
    dependents = sorted(
        (n for n in all_nodes.values() if n.kind == "dependent"),
        key=lambda nd: (nd.line, nd.display),
    )
    rendered = set()
    roots = []
    for root in dependents:
        entry = _node_json(root)
        if root.node_id in rendered:
            entry["already_shown"] = True
        else:
            rendered.add(root.node_id)
            entry["children"] = _children_json(root, all_nodes, {root.node_id}, 1, max_depth, rendered)
        roots.append(entry)
    return roots


def _dependents_json(node, all_nodes, reverse, visited, depth, max_depth, rendered):
    """See _children_json's docstring -- same "expand once, point to it
    afterward" fix, same reason (a shared independent parameter
    referenced from many dependent equations, e.g. one constant used
    across several pressure points, would otherwise have its whole
    reverse-dependents subtree re-embedded in full on every one of
    those references)."""
    if depth > max_depth:
        return [{"display": "... (max depth reached)", "tag": "note", "expr": None,
                  "line": None, "cycle": False, "unresolved": False, "already_shown": False, "children": []}]
    result = []
    for cid in reverse.get(node.node_id, []):
        child = all_nodes.get(cid)
        if child is None:
            continue
        entry = _node_json(child)
        entry["cycle"] = child.node_id in visited
        if not entry["cycle"]:
            if child.node_id in rendered:
                entry["already_shown"] = True
            else:
                rendered.add(child.node_id)
                entry["children"] = _dependents_json(child, all_nodes, reverse, visited | {child.node_id}, depth + 1, max_depth, rendered)
        result.append(entry)
    return result


def build_independent_tree_json(all_nodes, max_depth=25):
    reverse = {}
    for node in all_nodes.values():
        for ref_id in node.refs:
            reverse.setdefault(ref_id, []).append(node.node_id)

    roots = sorted(
        (n for n in all_nodes.values() if n.kind == "independent"),
        key=lambda nd: (nd.display, nd.line),
    )
    rendered = set()
    result = []
    for root in roots:
        entry = _node_json(root)
        if root.node_id in rendered:
            entry["already_shown"] = True
        else:
            rendered.add(root.node_id)
            entry["children"] = _dependents_json(root, all_nodes, reverse, {root.node_id}, 1, max_depth, rendered)
        result.append(entry)
    return result


HTML_PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title_escaped}</title>
<style>
  :root {{
    --bg: #f7f5f1;
    --panel: #ffffff;
    --ink: #2a2622;
    --ink-muted: #6b6459;
    --border: #e2ddd2;
    --accent: #b5502f;
    --independent: #3b7a4a;
    --independent-bg: rgba(59, 122, 74, 0.10);
    --dependent: #3b6ea5;
    --dependent-bg: rgba(59, 110, 165, 0.09);
    --fixed: #8a8072;
    --fixed-bg: rgba(138, 128, 114, 0.12);
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --bg: #1b1a18;
      --panel: #242220;
      --ink: #ece7de;
      --ink-muted: #a39a8c;
      --border: #38342c;
      --accent: #e8875f;
      --independent: #7fc492;
      --independent-bg: rgba(127, 196, 146, 0.13);
      --dependent: #7ba9e0;
      --dependent-bg: rgba(123, 169, 224, 0.12);
      --fixed: #b3a894;
      --fixed-bg: rgba(179, 168, 148, 0.14);
    }}
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--ink);
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
  .wrap {{ max-width: 1400px; margin: 0 auto; padding: 20px 24px 40px; }}
  h1 {{ font-size: 1.05rem; font-weight: 600; margin: 0 0 2px; }}
  .meta {{ color: var(--ink-muted); font-size: 0.82rem; margin-bottom: 16px; }}
  .toolbar {{ display: flex; gap: 10px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }}
  input#search {{ flex: 1; min-width: 220px; padding: 7px 10px; border-radius: 7px; border: 1px solid var(--border);
    background: var(--panel); color: var(--ink); font: inherit; }}
  button {{ padding: 6px 12px; border-radius: 7px; border: 1px solid var(--border); background: var(--panel);
    color: var(--ink); font: inherit; cursor: pointer; }}
  button:hover {{ border-color: var(--accent); }}
  .tabs {{ display: flex; gap: 8px; margin-bottom: 14px; }}
  .tab {{ padding: 7px 14px; border-radius: 7px 7px 0 0; border: 1px solid var(--border); border-bottom: none;
    background: var(--panel); color: var(--ink-muted); cursor: pointer; font-size: 0.86rem; }}
  .tab.active {{ color: var(--ink); font-weight: 600; }}
  .panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px 18px; }}
  .panel.hidden {{ display: none; }}
  code, .mono {{ font-family: "SF Mono", Consolas, Menlo, monospace; font-size: 0.82rem; }}
  ul.tree {{ list-style: none; margin: 0; padding-left: 20px; }}
  ul.tree.root {{ padding-left: 0; }}
  li {{ margin: 2px 0; }}
  li.hidden {{ display: none; }}
  .node-toggle {{ cursor: pointer; user-select: none; font-family: "SF Mono", Consolas, Menlo, monospace;
    font-size: 0.82rem; border-radius: 5px; padding: 1px 7px; display: inline-block; }}
  .node-toggle::before {{ content: "\\25B8 "; display: inline-block; transition: transform 0.1s; }}
  .node-toggle.open::before {{ transform: rotate(90deg); }}
  .node-toggle.leaf::before {{ content: "\\2022 "; }}
  .node-toggle.independent {{ color: var(--independent); background: var(--independent-bg); font-weight: 600; }}
  .node-toggle.fixed {{ color: var(--fixed); background: var(--fixed-bg); }}
  .node-toggle.dependent, .node-toggle.dependent_fixed {{ color: var(--dependent); background: var(--dependent-bg); }}
  .node-toggle.note {{ color: var(--ink-muted); font-style: italic; }}
  .line {{ color: var(--ink-muted); font-size: 0.74rem; }}
  .expr {{ color: var(--ink-muted); font-size: 0.78rem; font-family: "SF Mono", Consolas, Menlo, monospace; }}
  .cycle-note {{ color: var(--ink-muted); font-style: italic; font-size: 0.78rem; }}
  .children {{ display: none; }}
  .children.open {{ display: block; }}
  .legend {{ display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 12px; font-size: 0.78rem; color: var(--ink-muted); }}
  .legend span.swatch {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 4px; vertical-align: -1px; }}
  .stat-badge {{ display: inline-flex; align-items: baseline; gap: 6px; margin: 6px 0 10px;
    padding: 6px 14px; border-radius: 8px; background: var(--independent-bg);
    border: 1px solid var(--independent); }}
  .stat-badge .stat-num {{ font-size: 1.3rem; font-weight: 700; color: var(--independent); font-variant-numeric: tabular-nums; }}
  .stat-badge .stat-label {{ font-size: 0.82rem; color: var(--ink-muted); text-transform: uppercase; letter-spacing: 0.03em; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{title_escaped}</h1>
  <div class="stat-badge"><span class="stat-num">{n_refineable}</span><span class="stat-label">refineable independent parameters</span></div>
  <div class="meta">{ndependent} dependent roots &middot; {nindependent} independent roots &middot; {file_escaped}</div>
  <div class="toolbar">
    <input id="search" type="text" placeholder="Filter by name...">
    <button id="expandAll">Expand all</button>
    <button id="collapseAll">Collapse all</button>
  </div>
  <div class="legend">
    <div><span class="swatch" style="background:var(--independent)"></span>independent/refined</div>
    <div><span class="swatch" style="background:var(--dependent)"></span>dependent (equation)</div>
    <div><span class="swatch" style="background:var(--fixed)"></span>fixed</div>
  </div>
  <div class="tabs">
    <div class="tab active" data-panel="tree1">Tree 1 &middot; dependent &rarr; independent</div>
    <div class="tab" data-panel="tree2">Tree 2 &middot; independent &rarr; dependent</div>
  </div>
  <div class="panel" id="tree1"><div id="tree1Root"></div></div>
  <div class="panel hidden" id="tree2"><div id="tree2Root"></div></div>
</div>
<script>
const TREE1 = {tree1_json};
const TREE2 = {tree2_json};

function escapeHtml(s) {{
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}}

let uid = 0;
function renderNode(node) {{
  const li = document.createElement('li');
  const hasChildren = node.children && node.children.length > 0;
  const toggle = document.createElement('span');
  toggle.className = 'node-toggle ' + node.tag + (hasChildren ? '' : ' leaf');
  let label = node.display;
  if (node.unresolved) label += ' [unresolved reference]';
  toggle.appendChild(document.createTextNode(label));
  if (node.line) {{
    const lineSpan = document.createElement('span');
    lineSpan.className = 'line';
    lineSpan.textContent = '  (line ' + node.line + ')';
    toggle.appendChild(lineSpan);
  }}
  if (node.cycle) {{
    const cycleSpan = document.createElement('span');
    cycleSpan.className = 'cycle-note';
    cycleSpan.textContent = '  (cycle, stopping)';
    toggle.appendChild(cycleSpan);
  }} else if (node.already_shown) {{
    const shownSpan = document.createElement('span');
    shownSpan.className = 'cycle-note';
    shownSpan.textContent = '  (already shown above, see its own entry)';
    toggle.appendChild(shownSpan);
  }}
  li.appendChild(toggle);
  if (node.expr) {{
    const exprDiv = document.createElement('div');
    exprDiv.className = 'expr';
    exprDiv.style.marginLeft = '18px';
    exprDiv.textContent = '= ' + node.expr;
    li.appendChild(exprDiv);
  }}
  li.dataset.searchText = node.display.toLowerCase();
  if (hasChildren) {{
    const childWrap = document.createElement('div');
    childWrap.className = 'children';
    const ul = document.createElement('ul');
    ul.className = 'tree';
    for (const child of node.children) {{
      ul.appendChild(renderNode(child));
    }}
    childWrap.appendChild(ul);
    toggle.addEventListener('click', () => {{
      toggle.classList.toggle('open');
      childWrap.classList.toggle('open');
    }});
    li.appendChild(childWrap);
  }}
  return li;
}}

function renderRoots(container, roots) {{
  const ul = document.createElement('ul');
  ul.className = 'tree root';
  for (const root of roots) {{
    ul.appendChild(renderNode(root));
  }}
  container.appendChild(ul);
}}

renderRoots(document.getElementById('tree1Root'), TREE1);
renderRoots(document.getElementById('tree2Root'), TREE2);

for (const tab of document.querySelectorAll('.tab')) {{
  tab.addEventListener('click', () => {{
    for (const t of document.querySelectorAll('.tab')) t.classList.remove('active');
    for (const p of document.querySelectorAll('.panel')) p.classList.add('hidden');
    tab.classList.add('active');
    document.getElementById(tab.dataset.panel).classList.remove('hidden');
  }});
}}

document.getElementById('expandAll').addEventListener('click', () => {{
  for (const t of document.querySelectorAll('.node-toggle')) t.classList.add('open');
  for (const c of document.querySelectorAll('.children')) c.classList.add('open');
}});
document.getElementById('collapseAll').addEventListener('click', () => {{
  for (const t of document.querySelectorAll('.node-toggle')) t.classList.remove('open');
  for (const c of document.querySelectorAll('.children')) c.classList.remove('open');
}});

document.getElementById('search').addEventListener('input', (e) => {{
  const q = e.target.value.trim().toLowerCase();
  const allLis = document.querySelectorAll('li');
  if (!q) {{
    for (const li of allLis) li.classList.remove('hidden');
    return;
  }}
  for (const li of allLis) {{
    const matches = li.dataset.searchText && li.dataset.searchText.includes(q);
    li.classList.toggle('hidden', !matches);
    if (matches) {{
      let p = li.parentElement;
      while (p) {{
        if (p.classList && p.classList.contains('children')) {{
          p.classList.add('open');
          const sib = p.previousElementSibling;
          if (sib && sib.classList.contains('node-toggle')) sib.classList.add('open');
        }}
        if (p.tagName === 'LI') p.classList.remove('hidden');
        p = p.parentElement;
      }}
    }}
  }}
}});
</script>
</body>
</html>
"""


def build_html(all_nodes, inp_file, clean, max_depth=25):
    tree1 = build_dependent_tree_json(all_nodes, max_depth=max_depth)
    tree2 = build_independent_tree_json(all_nodes, max_depth=max_depth)
    ndependent = sum(1 for n in all_nodes.values() if n.kind == "dependent")
    # "independent" here means "not a dependent equation" -- it includes
    # BOTH refined ('@'/bare-named) AND '!'-fixed independent parameters
    # (see _tag()). The highlighted badge is specifically the REFINEABLE
    # subset (kind == independent and not fixed) -- the same definition
    # find_refined_params.py uses -- since that's what "how many parameters
    # is this refinement actually varying" means; a '!'-fixed independent
    # parameter never moves, so counting it there would overstate it.
    #
    # Both counts additionally weight by for-loop repetition ('for xdds
    # { ... }' / 'for strs [N to M] { ... }') -- a node declared once in a
    # loop body is really node.scoped and True ? multiple independent
    # copies at runtime : still just one shared parameter (TOPAS's 'same
    # name = same value' rule), confirmed empirically against a real file
    # -- see find_refined_params.loop_multiplier()'s docstring for the
    # full evidence. cis.for_loop_multiplier_at_line returns 1 for any
    # node not inside such a loop at all, so this is a no-op elsewhere.
    for_loop_spans = cis.find_for_loop_multipliers(clean)

    def node_mult(n):
        if not n.scoped:
            return 1
        return cis.for_loop_multiplier_at_line(n.line, clean, for_loop_spans)

    nindependent = sum(node_mult(n) for n in all_nodes.values() if n.kind == "independent")
    n_refineable = sum(node_mult(n) for n in all_nodes.values() if n.kind == "independent" and not n.fixed)
    title = f"Parameter dependency trees -- {os.path.basename(inp_file)}"
    return HTML_PAGE_TEMPLATE.format(
        title_escaped=title.replace("<", "&lt;").replace(">", "&gt;"),
        file_escaped=inp_file.replace("<", "&lt;").replace(">", "&gt;"),
        ndependent=ndependent,
        nindependent=nindependent,
        n_refineable=n_refineable,
        tree1_json=json.dumps(tree1),
        tree2_json=json.dumps(tree2),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inp_file")
    parser.add_argument("-o", "--output", help="write the report to this file instead of stdout")
    parser.add_argument("--tree", choices=["dependent", "independent", "both"], default="both")
    parser.add_argument("--run-number", type=int, default=0)
    parser.add_argument("--no-open", action="store_true",
                         help="don't open/focus the report in VS Code afterward (default: do open it, only when -o is given)")
    args = parser.parse_args()

    all_nodes, warnings, clean = build_graph(args.inp_file, run_number=args.run_number)

    if args.output and os.path.splitext(args.output)[1].lower() in (".html", ".htm"):
        html = build_html(all_nodes, args.inp_file, clean)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Written to {args.output}", file=sys.stderr)
        if not args.no_open:
            # HTML output opens in the default browser -- unlike the
            # plain-text report below, which opens in VS Code. Matches
            # this skill's own established convention (see
            # topas_keyword_tree.py/plot_xy.py): text reports -> VS Code,
            # HTML visualizations -> browser.
            abs_path = os.path.abspath(args.output)
            if os.name == "nt":
                os.startfile(abs_path)
            else:
                opener = "open" if sys.platform == "darwin" else "xdg-open"
                opener_path = shutil.which(opener)
                if opener_path:
                    subprocess.run([opener_path, abs_path], check=False)
        return

    out = []
    if args.tree in ("dependent", "both"):
        out.append(f"TREE 1 -- dependent parameters/keywords with independent (or fixed) children")
        out.append(f"({sum(1 for n in all_nodes.values() if n.kind == 'dependent')} dependent roots)")
        out.append("=" * 78)
        out.append("")
        render_dependent_tree(all_nodes, out)

    if args.tree == "both":
        out.append("")
        out.append("")

    if args.tree in ("independent", "both"):
        out.append(f"TREE 2 -- independent parameters with dependent children")
        out.append(f"({sum(1 for n in all_nodes.values() if n.kind == 'independent')} independent roots)")
        out.append("=" * 78)
        out.append("")
        render_independent_tree(all_nodes, out)

    if warnings:
        out.append("")
        out.append(f"Macro-expansion warnings ({len(warnings)}):")
        for w in warnings:
            out.append(f"  {w}")

    report = "\n".join(out) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Written to {args.output}", file=sys.stderr)
        if not args.no_open:
            # Matches format_inp_hierarchy.py's own established convention
            # (see module docstring): shutil.which() resolves "code.cmd" on
            # Windows the way a real shell would, which a bare
            # subprocess.run(["code", ...]) does not find on its own.
            code_path = shutil.which("code") or shutil.which("code.cmd")
            if code_path:
                subprocess.run([code_path, args.output], check=False)
            else:
                print("Note: 'code' CLI not found on PATH -- couldn't open the report in VS Code.", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
