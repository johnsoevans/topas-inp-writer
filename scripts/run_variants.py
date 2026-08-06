#!/usr/bin/env python3
"""
run_variants.py -- run several model variants of one TOPAS .inp and print a
comparison table.

Each variant is a text transform applied to a scratch copy of the base file.
The original .inp is never modified. For every variant the runner:

  - strips any stale `C_matrix_normalized` block
  - rewrites the `xdd` data path to an absolute one, so the copy runs from
    the scratch directory
  - removes the output-writing macro calls it recognizes (`Out_X_Yobs`,
    `Out_X_Ycalc`, `Out_X_Difference`, `Create_hklm_d_Th2_Ip_file`,
    `Create_hklm_d_Th2_IScaled_file`, `Out_CIF_STR`), since the comparison
    needs only the numbers in the table -- pass `keep_outputs=True` to write
    them instead, under per-variant filenames
  - writes `<workdir>/v_<name>.inp`, runs tc.exe, and scrapes the result

An unmodified `base` row is always run first and every other row is reported
as a delta against it.

Reported per variant:

    Rwp     r_wp from the resulting .out
    dRwp    Rwp minus the base row's Rwp
    GoF     gof from the resulting .out
    Npar    TOPAS's own "Num independent parameters: N" console line
    limits  any parameter name carrying _LIMIT_MIN_ / _LIMIT_MAX_ in the .out

Npar sits next to dRwp so the cost of a variant is visible alongside its gain;
`limits` flags a variant whose improvement rests on a saturated parameter
(see R35/R36/R37 in references/27-rietveld-workflow-conventions.md).

Usage as a library (the normal case -- transforms are problem-specific):

    import sys; sys.path.insert(0, r"<skill>/scripts")
    from run_variants import VariantRunner, add_to_str, add_to_xdd, set_bkg, comment_out

    r = VariantRunner("y2o3.inp", workdir="y2o3_workings")
    r.add("sh4",   lambda t: add_to_str(t, "PO_Spherical_Harmonics(sh, 4)"))
    r.add("sh6",   lambda t: add_to_str(t, "PO_Spherical_Harmonics(sh, 6)"))
    r.add("steph", lambda t: add_to_str(t, "Stephens_cubic(@,0.5, @,0.0001, @,0.0001)"))
    r.add("b16",   lambda t: set_bkg(t, 16))
    r.run()

`run()` prints the table and returns the list of result dicts.

This runs variants and reports numbers. It does not choose what to vary, pick
a winner, or edit the base file.
"""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import topas_install

C_MATRIX_RE = re.compile(r"C_matrix_normalized\s*\{.*?\n\}", re.S)
XDD_RE = re.compile(r"^(\s*xdd\s+)(\"[^\"]+\"|\S+)", re.M)
NPAR_RE = re.compile(r"Num independent parameters:\s*(\d+)")
LIMIT_RE = re.compile(r"^\s*(?:\S+\s+)*?([A-Za-z_]\w*)[^\n]*_LIMIT_(?:MIN|MAX)_", re.M)

# Output-writing macros whose filename argument is rewritten per variant.
OUTPUT_MACROS = ("Out_X_Yobs", "Out_X_Ycalc", "Out_X_Difference",
                 "Create_hklm_d_Th2_Ip_file", "Create_hklm_d_Th2_IScaled_file",
                 "Out_CIF_STR")


# --------------------------------------------------------------------------
# text helpers -- deliberately literal string surgery, not an .inp parser
# --------------------------------------------------------------------------

def add_to_str(text, block, indent="      "):
    """Insert `block` as a new line inside the first `str { }` phase, just
    before its site list ends -- placed ahead of the first output macro or
    `for strs` if present, otherwise appended after the last `site` line."""
    for marker in [m + "(" for m in OUTPUT_MACROS] + ["for strs"]:
        i = text.find(marker)
        if i != -1:
            line_start = text.rfind("\n", 0, i) + 1
            return text[:line_start] + indent + block + "\n" + text[line_start:]
    sites = list(re.finditer(r"^[^\n]*\bsite\b[^\n]*$", text, re.M))
    if not sites:
        raise ValueError("add_to_str: found no site list or output macro to anchor to")
    end = sites[-1].end()
    return text[:end] + "\n" + indent + block + text[end:]


def add_to_xdd(text, block, indent="   "):
    """Insert `block` as a new line at xdd level, immediately before the
    first `str` / `hkl_Is` / `xo_Is` phase block."""
    m = re.search(r"^\s*(str|hkl_Is|xo_Is)\b", text, re.M)
    if not m:
        raise ValueError("add_to_xdd: found no str/hkl_Is/xo_Is phase to insert before")
    line_start = text.rfind("\n", 0, m.start()) + 1
    return text[:line_start] + indent + block + "\n" + text[line_start:]


def set_bkg(text, n_terms):
    """Replace the Chebyshev `bkg` line with `n_terms` refined zero coefficients."""
    new = "\n   bkg @" + " 0" * n_terms + "\n"
    out, count = re.subn(r"\n\s*bkg\s+@[^\n]*\n", new, text, count=1)
    if not count:
        raise ValueError("set_bkg: no 'bkg @ ...' line found")
    return out


def comment_out(text, pattern):
    """Comment out every whole line matching `pattern` (a regex)."""
    rx = re.compile(pattern)
    return "\n".join(("'" + ln) if rx.search(ln) and not ln.lstrip().startswith("'") else ln
                     for ln in text.split("\n"))


# --------------------------------------------------------------------------

def _find_tc():
    root, found = topas_install.get_topas_dir()
    if found:
        for exe in ("tc.exe", "TC.EXE", "tc"):
            p = os.path.join(root, exe)
            if os.path.exists(p):
                return p
    raise SystemExit("Could not locate tc.exe -- set TOPAS_DIR to your TOPAS install root.")


class VariantRunner:
    def __init__(self, base_inp, workdir=None, tc_path=None, data_dir=None,
                 keep_outputs=False):
        """`data_dir` is where the base file's relative `xdd` path resolves
        from; it defaults to the base file's own directory, matching TOPAS.
        Set it when the base .inp is itself a scratch copy sitting somewhere
        other than next to its data.

        `keep_outputs=False` (the default) removes the output-writing macro
        calls from each variant, since the comparison only needs the numbers
        in the table. On a 15k-point pattern each variant would otherwise
        write ~800 kB of Yobs/Ycalc, which buries the real deliverables in
        the working directory. Set True to keep them (written under
        per-variant filenames) when a variant's fit needs plotting; or just
        re-run the one variant of interest afterwards."""
        self.base_inp = os.path.abspath(base_inp)
        self.base_dir = os.path.dirname(self.base_inp)
        self.stem = os.path.splitext(os.path.basename(self.base_inp))[0]
        self.data_dir = os.path.abspath(data_dir) if data_dir else self.base_dir
        self.workdir = os.path.abspath(workdir) if workdir else self.base_dir
        self.keep_outputs = keep_outputs
        os.makedirs(self.workdir, exist_ok=True)
        self.tc = tc_path or _find_tc()
        self.variants = []
        with open(self.base_inp, encoding="utf-8") as f:
            self.base_text = C_MATRIX_RE.sub("", f.read())
        # Fail once, up front, with a clear message -- rather than letting
        # every variant fail identically with the same tc.exe error.
        m = XDD_RE.search(self.base_text)
        if m and not os.path.isabs(m.group(2).strip('"')):
            resolved = os.path.join(self.data_dir, m.group(2).strip('"'))
            if not os.path.exists(resolved):
                raise SystemExit(
                    "Data file not found: %s\n"
                    "(the base .inp's xdd path resolves against %s -- pass "
                    "data_dir=... if the data lives elsewhere)" % (resolved, self.data_dir))

    def add(self, name, transform):
        """Register a variant. `transform` takes the base text, returns new text."""
        self.variants.append((name, transform))
        return self

    def _prepare(self, name, transform):
        text = XDD_RE.sub(
            lambda m: m.group(1) + '"' + os.path.join(
                self.data_dir, m.group(2).strip('"')) + '"', self.base_text, count=1)
        for macro in OUTPUT_MACROS:
            if self.keep_outputs:
                text = re.sub(
                    re.escape(macro) + r"\(([^),]*)\)",
                    lambda m, mc=macro: "%s(%s)" % (mc, os.path.join(
                        self.workdir, "%s_%s_%s%s" % (self.stem, name, mc,
                                                      os.path.splitext(m.group(1).strip())[1] or ".txt"))),
                    text)
            else:
                # Delete just the call, not the whole line -- an output macro
                # can share a line with something that must survive.
                text = re.sub(re.escape(macro) + r"\([^)]*\)", "", text)
        text = transform(text)
        # Scratch name carries the base file's stem, so two runners sharing one
        # workdir don't overwrite each other's variants (notably the 'base' row).
        path = os.path.join(self.workdir, "v_%s_%s.inp" % (self.stem, name))
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path

    def _run_one(self, name, transform):
        path = self._prepare(name, transform)
        proc = subprocess.run([self.tc, path], capture_output=True, text=True)
        npar = NPAR_RE.search(proc.stdout or "")
        out_path = path[:-4] + ".out"
        if not os.path.exists(out_path):
            tail = (proc.stdout or proc.stderr or "").strip().splitlines()[-4:]
            return {"name": name, "error": " | ".join(tail) or "tc.exe produced no .out"}
        out_text = open(out_path, encoding="utf-8").read()
        rwp = re.search(r"\br_wp\s+([\d.eE+-]+)", out_text)
        gof = re.search(r"\bgof\s+([\d.eE+-]+)", out_text)
        limits = sorted(set(LIMIT_RE.findall(out_text)))
        return {"name": name, "error": None, "inp": path, "out": out_path,
                "rwp": float(rwp.group(1)) if rwp else None,
                "gof": float(gof.group(1)) if gof else None,
                "npar": int(npar.group(1)) if npar else None,
                "limits": limits}

    def run(self, echo=True):
        results = [self._run_one("base", lambda t: t)]
        for name, transform in self.variants:
            results.append(self._run_one(name, transform))
        if echo:
            print(self.format_table(results))
        return results

    @staticmethod
    def format_table(results):
        base = next((r for r in results if r["name"] == "base" and not r["error"]), None)
        w = max([len(r["name"]) for r in results] + [7])
        lines = ["%-*s %9s %8s %8s %6s  %s" % (w, "variant", "Rwp", "dRwp", "GoF", "Npar", "limits")]
        for r in results:
            if r["error"]:
                lines.append("%-*s %9s %8s %8s %6s  %s" % (w, r["name"], "FAILED", "", "", "", r["error"]))
                continue
            if base and r is not base and r["rwp"] is not None and base["rwp"] is not None:
                d = "%+.4f" % (r["rwp"] - base["rwp"])
            else:
                d = "-"
            lines.append("%-*s %9.4f %8s %8.4f %6s  %s" % (
                w, r["name"], r["rwp"], d, r["gof"],
                r["npar"] if r["npar"] is not None else "?",
                ", ".join(r["limits"]) if r["limits"] else "-"))
        return "\n".join(lines)


if __name__ == "__main__":
    print(__doc__)
