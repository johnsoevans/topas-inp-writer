#!/usr/bin/env python3
"""
topilot_wizard.py -- collect the fields needed to write a TOPAS .inp and write
them to a JSON job file.

This dialog holds NO TOPAS knowledge and no Claude coupling. It is a form that
writes JSON. All refinement knowledge lives in the topas-inp-writer skill and
in the /topas-wizard slash command.

    python topilot_wizard.py [--out <path to job file>] [--workflow rietveld]

--out is an optional testing override. In normal use the wizard derives the job
file's path itself from the data file chosen in the form, so a caller cannot
supply it -- it has no idea which folder the user will pick.

On exit 0 the job file's path is printed to stdout, followed by the JSON.

Exit codes:
    0   job file written
    1   error
    2   cancelled
    3   timed out

THE CENTRAL CONTRACT: an optional field left alone is "(not specified)", which
means "Claude decides" -- NOT "off". Unset fields are OMITTED from the job file
rather than written as null, because an absent key cannot be mistaken for a
guessed value. Anything explicitly set is binding and used as given.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import json
import os
import re
import sys
import tomllib
import traceback
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, font as tkfont, messagebox, ttk

HERE = Path(__file__).resolve().parent
SCHEMA = 2                            # 2: "workflows" is a list; see ANALYSES
WATCHDOG_MS = 30 * 60 * 1000          # 30 minutes; see EXIT_TIMEOUT
CREATE_NEW_CONSOLE = 0x00000010       # win32: give the CLI its own window
EXIT_OK, EXIT_ERROR, EXIT_CANCEL, EXIT_TIMEOUT = 0, 1, 2, 3

NOT_SPECIFIED = "(not specified)"

# Floor for the field column in sections 3 and 4. It has to clear the widest
# control either section leaves in that column, or the two end up different
# widths -- see the spacer note in _build_measurement.
FIELD_COL_MIN = 260


def sg_display(symbol: str) -> str:
    """Capitalise the leading centring letter (P, I, F, A, B, C, R); sgcom5
    stores all lower case. Display only -- tc.exe accepts either."""
    return symbol[:1].upper() + symbol[1:] if symbol else symbol
NO_INSTRUMENT = "None specified — describe it in section 2"
PICK_INSTRUMENT = "— Select instrument —"
PF_METHOD_DEFAULT = "Choose…"

# The three peak-shape families, offered on both tabs so they stay in step.
PEAK_SHAPES = [("TCHZ pseudo-Voigt", "tchz"),
               ("Fundamental parameters", "fp"),
               ("Size / microstrain only (no TCHZ)", "size_strain")]

# Derived from PEAK_SHAPES, not duplicated, so the two lists cannot drift
# apart. A shape per reflection only means something in an empirical xo_Is fit.
PEAK_SHAPES_PEAKFIT = PEAK_SHAPES + [("One pseudo-Voigt per peak", "pv_per_peak")]

DATA_FILETYPES = [
    ("Powder data", "*.xye *.xy *.raw *.brml *.xrdml"),
    ("All files", "*.*"),
]
DATA_SUFFIXES = {".xye", ".xy", ".raw", ".brml", ".xrdml"}

# The analysis tabs, left to right. THE ORDER IS THE PIPELINE ORDER: a job runs
# whichever stages are ticked, in this sequence. Future has no checkbox.
ANALYSES = [("peak_fitting", "  Peak Fit/Index  "),
            ("solve",        "  Solve  "),
            ("rietveld",     "  Riet/Pawley/Quant  "),
            ("pdf",          "  PDF  "),
            ("seq_para",     "  Seq/Para  ")]

# Seq/Para is a MODIFIER, not a stage: excluded from STAGES and emitted as its
# own key. It needs a refinement to repeat -- hence SEQ_NEEDS.
STAGES = [k for k, _ in ANALYSES if k != "seq_para"]
SEQ_NEEDS = ("rietveld", "pdf")

# PDF fits G(r), not a powder pattern, so it shares no data model with the
# pattern stages and cannot be combined with them.
PDF_EXCLUDES = ("peak_fitting", "solve", "rietveld")

# Which stages name the output file. Solve never does -- it feeds the
# refinement that does.
FIT_STAGES = ("rietveld", "pdf")

SEQ_MODES = [("One .inp with #list instructions", "list"),
             ("One .inp per dataset", "per_dataset"),
             ("One parametric .inp fitting all data at once", "parametric")]

# Charge flipping solves from the data without a structural model, so the
# extended/molecular choice below applies only to simulated annealing.
SOLVE_METHODS = [("Simulated annealing", "simulated_annealing"),
                 ("Charge flipping", "charge_flipping")]

# Built-in defaults, shipped in code so a deleted or broken config file is a
# non-event. Only values-when-enabled live here; assertions stay unset.
BUILTIN = {
    "general": {"mode": "create_and_run"},
    "measurement": {},
    "rietveld": {"rules": "rietveld"},
    # A CW upper limit, not a universal one: 70 deg is past the useful data
    # on a lab Cu pattern. Blank on ToF, where the axis is not degrees.
    "corrections": {"two_theta_max": 70},
    "peak_shape": {"sample_size_strain": False, "axial_length": 6,
                   "refine_axial": True},
    "refinement": {"background_order": 6, "iters_create_only": 0,
                   "iters_run": 1000},
    "phases": {"confidence": "definite", "refine_cell": True, "po": "none",
               "po_order": 4, "beq_by_type": False},
}


# --------------------------------------------------------------------------
# Configuration loading
# --------------------------------------------------------------------------

def _deep_merge(base: dict, overlay: dict) -> dict:
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for k, v in overlay.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(warnings: list[str]) -> dict:
    """built-in -> wizard_defaults.toml -> .local.json. Never raises; a bad
    hand-edited file warns and falls back."""
    cfg = _deep_merge({}, BUILTIN)

    toml_path = HERE / "wizard_defaults.toml"
    if toml_path.is_file():
        try:
            cfg = _deep_merge(cfg, tomllib.loads(toml_path.read_text(encoding="utf-8")))
        except Exception as exc:
            warnings.append(f"{toml_path.name}: {exc} -- using built-in defaults")

    local_path = HERE / "wizard_defaults.local.json"
    if local_path.is_file():
        try:
            cfg = _deep_merge(cfg, json.loads(local_path.read_text(encoding="utf-8")))
        except Exception as exc:
            warnings.append(f"{local_path.name}: {exc} -- ignored")
    return cfg


def save_local(cfg_patch: dict) -> None:
    """Write the local JSON, never the TOML: a round-trip kills its comments."""
    path = HERE / "wizard_defaults.local.json"
    existing = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
    path.write_text(json.dumps(_deep_merge(existing, cfg_patch), indent=2),
                    encoding="utf-8")


def load_instruments(warnings: list[str]) -> list[dict]:
    path = HERE / "instrument_descriptions.toml"
    if not path.is_file():
        warnings.append(f"{path.name} not found -- instrument list is empty")
        return []
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        warnings.append(f"{path.name}: {exc} -- instrument list is empty")
        return []
    out = []
    for entry in data.get("instrument", []):
        if "name" in entry:
            out.append(entry)
        else:
            warnings.append(f"{path.name}: an [[instrument]] has no name -- skipped")
    return out


def load_space_groups(warnings: list[str]) -> list[tuple[str, str]]:
    """(symbol, crystal_system) from TOPAS's sgcom5.txt, via
    generate_space_group_browser's parser. ~25 ms, so no caching."""
    try:
        sys.path.insert(0, str(HERE))
        from generate_space_group_browser import find_sgcom5, parse_sgcom5
        text = find_sgcom5(None).read_text(encoding="utf-8")
        pairs = []
        for rec in parse_sgcom5(text):
            system = str(rec.get("system", "")).lower()
            for sym in rec.get("symbols", []):
                pairs.append((sym, system))
        return pairs
    except SystemExit as exc:                      # find_sgcom5 exits if unset
        warnings.append(f"space groups: {exc} -- free text only")
    except Exception as exc:
        warnings.append(f"space groups: {exc} -- free text only")
    return []


# Independent cell parameters per crystal system. Everything else is derived,
# so the form greys it out and fills it from the free ones.
CELL_FREEDOM = {
    "cubic":        ["a"],
    "tetragonal":   ["a", "c"],
    "hexagonal":    ["a", "c"],
    "trigonal":     ["a", "c"],
    "rhombohedral": ["a", "al"],
    "orthorhombic": ["a", "b", "c"],
    "monoclinic":   ["a", "b", "c", "be"],
    "triclinic":    ["a", "b", "c", "al", "be", "ga"],
}
CELL_KEYS = ["a", "b", "c", "al", "be", "ga"]


def derive_cell(system: str, values: dict) -> dict:
    """Fill dependent cell parameters from the free ones."""
    sysname = (system or "triclinic").lower()
    free = CELL_FREEDOM.get(sysname, CELL_FREEDOM["triclinic"])
    out = dict(values)
    a = values.get("a")
    if sysname in ("cubic",):
        out["b"] = out["c"] = a
        out["al"] = out["be"] = out["ga"] = 90.0
    elif sysname in ("tetragonal",):
        out["b"] = a
        out["al"] = out["be"] = out["ga"] = 90.0
    elif sysname in ("hexagonal", "trigonal"):
        out["b"] = a
        out["al"] = out["be"] = 90.0
        out["ga"] = 120.0
    elif sysname == "rhombohedral":
        out["b"] = out["c"] = a
        out["be"] = out["ga"] = values.get("al")
    elif sysname == "orthorhombic":
        out["al"] = out["be"] = out["ga"] = 90.0
    elif sysname == "monoclinic":
        out["al"] = out["ga"] = 90.0
    return out, free


# --------------------------------------------------------------------------
# Small widgets
# --------------------------------------------------------------------------

class Tooltip:
    """Hover help, sourced from topas-editor's hovertext_help.md when present
    so both tools read alike. Absent file -> no tooltip."""

    def __init__(self, widget, text: str):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _evt=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        ttk.Label(self.tip, text=self.text, relief="solid", borderwidth=1,
                  wraplength=380, justify="left", padding=(6, 4)).pack()

    def _hide(self, _evt=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


def load_hovertext() -> dict[str, str]:
    """Parse topas-editor's hovertext_help.md into {keyword: explanation}."""
    for cand in (
        HERE.parent.parent.parent / "topas-editor" / "assets" / "hovertext_help.md",
        HERE.parent / "assets" / "hovertext_help.md",
    ):
        if cand.is_file():
            try:
                out, key, buf = {}, None, []
                for line in cand.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.startswith("#"):
                        if key:
                            out[key] = " ".join(buf).strip()
                        key, buf = line.lstrip("#").strip().split()[0] if line.lstrip("#").strip() else None, []
                    elif key:
                        buf.append(line.strip())
                if key:
                    out[key] = " ".join(buf).strip()
                return {k: v for k, v in out.items() if v}
            except Exception:
                return {}
    return {}


class Scrollable(ttk.Frame):
    """Vertically scrolling frame (ttk has none). Tab content only -- the
    shared blocks stay outside so OK can never scroll off screen."""

    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._bar = ttk.Scrollbar(self, orient="vertical",
                                  command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._on_scroll)
        self.body = ttk.Frame(self._canvas)
        self._win = self._canvas.create_window((0, 0), window=self.body,
                                               anchor="nw")
        self.body.bind("<Configure>", self._on_body)
        self._canvas.bind("<Configure>", self._on_canvas)
        self._canvas.bind("<Enter>", lambda _e: self._bind_wheel(True))
        self._canvas.bind("<Leave>", lambda _e: self._bind_wheel(False))

    def _on_scroll(self, first, last):
        # Show the bar only when there is something to scroll to.
        if float(first) <= 0.0 and float(last) >= 1.0:
            self._bar.grid_remove()
        else:
            self._bar.grid(row=0, column=1, sticky="ns")
        self._bar.set(first, last)

    def set_view_height(self, height: int):
        """A Canvas requests no height of its own, so a scroller placed in a
        resizable window collapses to nothing. Ask for one explicitly."""
        self._canvas.configure(height=height)

    def body_height(self) -> int:
        self.body.update_idletasks()
        return self.body.winfo_reqheight()

    def _on_body(self, _evt=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas(self, evt):
        self._canvas.itemconfigure(self._win, width=evt.width)

    def _bind_wheel(self, on):
        if on:
            self._canvas.bind_all("<MouseWheel>", self._wheel)
        else:
            self._canvas.unbind_all("<MouseWheel>")

    def _wheel(self, evt):
        first, last = self._canvas.yview()
        if first <= 0.0 and last >= 1.0:
            return                     # nothing to scroll; let the event pass
        self._canvas.yview_scroll(int(-evt.delta / 120), "units")


class CollapsibleGroup(ttk.Frame):
    """A titled group that folds away. All three optional groups ship closed, so
    the window opens short and never needs to grow past the screen edge."""

    def __init__(self, parent, title: str, **kw):
        super().__init__(parent, **kw)
        self._open = tk.BooleanVar(value=False)
        self._btn = ttk.Checkbutton(self, style="Toolbutton", command=self._toggle,
                                    variable=self._open)
        self._btn.grid(row=0, column=0, sticky="ew")
        self.body = ttk.Frame(self, padding=(16, 4, 4, 8))
        self.columnconfigure(0, weight=1)
        self._title = title
        self._sync()

    def _sync(self):
        arrow = "▼" if self._open.get() else "▶"
        self._btn.configure(text=f"  {arrow}  {self._title}")

    def _toggle(self):
        self._sync()
        if self._open.get():
            self.body.grid(row=1, column=0, sticky="ew")
        else:
            self.body.grid_forget()


class TriState(ttk.Combobox):
    """(not specified) / one / the other. A checkbox cannot express the
    first, so it would silently assert the unticked value."""

    def __init__(self, parent, options: list[tuple[str, str]], **kw):
        # options: [(label, stored_value), ...]
        super().__init__(parent, state="readonly", **kw)
        self.set_options(options)

    def set_options(self, options: list[tuple[str, str]]):
        """Replace the choices. Any current value that is no longer offered
        falls back to (not specified) rather than lingering as a stale one."""
        keep = self.value() if hasattr(self, "_map") else None
        self._map = {NOT_SPECIFIED: None}
        labels = [NOT_SPECIFIED]
        for label, value in options:
            self._map[label] = value
            labels.append(label)
        self._rev = {v: k for k, v in self._map.items()}
        self.configure(values=labels)
        self.set_value(keep if keep in self._rev else None)

    def value(self):
        return self._map.get(self.get())

    def set_value(self, value):
        self.set(self._rev.get(value, NOT_SPECIFIED))


def yes_no(parent, **kw) -> TriState:
    return TriState(parent, [("Yes", True), ("No", False)], **kw)


def req(parent, text: str, **kw) -> ttk.Frame:
    """Compulsory field label: text plus a red asterisk. Two channels, so the
    meaning survives without colour."""
    row = ttk.Frame(parent, **kw)
    ttk.Label(row, text=text).pack(side="left")
    ttk.Label(row, text=" *", style="Req.TLabel").pack(side="left")
    return row


def wrap_to_width(label: ttk.Label, margin: int = 28) -> None:
    """Wrap a note at the window edge instead of at a fixed column. A literal
    wraplength breaks the line early on any window wider than it was chosen
    for; this follows the container's actual width."""
    def _on(evt):
        width = max(200, evt.width - margin)
        if int(label.cget("wraplength") or 0) != width:
            label.configure(wraplength=width)
    label.master.bind("<Configure>", _on, add="+")


def bind_text_revalidate(widget: tk.Text, validate) -> None:
    """tk.Text has no textvariable to trace, unlike every Entry in this form,
    so nothing calls validate() as the user types or pastes into one -- the
    status line and OK button then go stale until some unrelated control
    happens to touch the form. <<Paste>> is also bound because a mouse-menu
    paste fires no key event; the 1 ms defer lets the pasted text land first,
    since <<Paste>> fires before the widget's own insert on some Tk builds."""
    widget.bind("<KeyRelease>", lambda _e: validate(), add="+")
    widget.bind("<<Paste>>", lambda _e: widget.after(1, validate), add="+")


def num_or_none(text: str, cast=float):
    text = (text or "").strip()
    if not text:
        return None
    try:
        value = cast(text)
    except ValueError:
        return None
    # 10.0 and 10 mean the same thing to TOPAS, but 10 is what a person wrote.
    if cast is float and isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def as_posix(path: str | None) -> str | None:
    """Forward slashes everywhere. Windows backslashes survive a JSON round-trip
    only as escaped pairs, and TOPAS accepts forward slashes on every platform."""
    if not path:
        return None
    return Path(path).as_posix()


# --------------------------------------------------------------------------
# Per-phase settings dialog
# --------------------------------------------------------------------------

class CellSymmetry(ttk.Frame):
    """Space group plus unit cell, with the dependent axes greying out and
    filling themselves from the group's crystal system. Shared by
    PhaseSettingsDialog and the Solve tab so the two cannot drift apart."""

    def __init__(self, parent, space_groups, cell=None, symbol=""):
        super().__init__(parent)
        self.space_groups = space_groups

        ttk.Label(self, text="Space group").grid(row=0, column=0, sticky="w")
        self.sg_var = tk.StringVar(value=symbol or "")
        self.sg_box = ttk.Combobox(self, textvariable=self.sg_var, width=22,
                                   values=[sg_display(sym) for sym, _ in space_groups])
        self.sg_box.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.sg_var.trace_add("write", lambda *_: self.sync())
        self.sys_lbl = ttk.Label(self, text="", foreground="grey")
        self.sys_lbl.grid(row=0, column=2, columnspan=2, sticky="w", padx=(8, 0))

        ttk.Label(self, text="Unit cell").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.cell_vars, self.cell_entries = {}, {}
        cell = cell or {}
        for i, key in enumerate(CELL_KEYS):
            sub = ttk.Frame(self)
            sub.grid(row=2 + i // 3, column=i % 3, sticky="w", pady=2)
            ttk.Label(sub, text=key, width=3).pack(side="left")
            var = tk.StringVar(value=("" if cell.get(key) is None else str(cell[key])))
            ent = ttk.Entry(sub, textvariable=var, width=11)
            ent.pack(side="left")
            self.cell_vars[key], self.cell_entries[key] = var, ent
        self.sync()

    def system(self) -> str:
        sym = self.sg_var.get().strip().lower()
        for symbol, system in self.space_groups:
            if symbol == sym:             # stored symbols are lower case
                return system
        return ""

    def sync(self):
        """Only the axes the crystal system leaves free stay editable; an empty
        or unrecognised symbol falls back to triclinic, so all six are live."""
        system = self.system()
        self.sys_lbl.configure(text=system or "(unrecognised symbol)")
        _, free = derive_cell(system, {})
        for key, ent in self.cell_entries.items():
            ent.configure(state="normal" if key in free else "disabled")

    def value(self) -> dict:
        system = self.system()
        raw = {k: num_or_none(v.get()) for k, v in self.cell_vars.items()}
        filled, _ = derive_cell(system, raw)
        return {"space_group": self.sg_var.get().strip(),
                "crystal_system": system, "cell": filled}

    def set_value(self, d: dict):
        """Fill from a value() dict. The symbol goes in FIRST so its trace runs
        sync() and un-greys the dependent axes before they are written."""
        self.sg_var.set(d.get("space_group") or "")
        self.sync()
        cell = d.get("cell") or {}
        for key, var in self.cell_vars.items():
            var.set("" if cell.get(key) is None else str(cell[key]))

    def complete(self) -> bool:
        v = self.value()
        return bool(v["space_group"] and v["crystal_system"]
                    and all(x is not None for x in v["cell"].values()))


class PhaseSettingsDialog(tk.Toplevel):
    """One phase's own settings: Pawley cell and symmetry, plus its optional
    corrections. Per-phase because a shared PO correction would be wrong."""

    def __init__(self, parent, row, space_groups, cfg):
        super().__init__(parent)
        self.title(f"Phase settings — {row.name_var.get() or 'unnamed'}")
        self.transient(parent)
        self.row, self.space_groups, self.cfg = row, space_groups, cfg
        self.result = None
        s = dict(row.settings)

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)
        r = 0

        self.is_pawley = row.source_var.get() == "pawley"
        if self.is_pawley:
            ttk.Label(frm, text="Pawley phase — cell and symmetry are required",
                      font=("Segoe UI", 9, "bold")).grid(row=r, column=0, columnspan=4,
                                                         sticky="w", pady=(0, 8))
            r += 1
            self.cellsym = CellSymmetry(frm, space_groups, s.get("cell"),
                                        s.get("space_group", ""))
            self.cellsym.grid(row=r, column=0, columnspan=4, sticky="w")
            r += 1

            self.refine_cell = tk.BooleanVar(
                value=s.get("refine_cell", cfg["phases"]["refine_cell"]))
            ttk.Checkbutton(frm, text="Refine the cell",
                            variable=self.refine_cell).grid(row=r, column=0, columnspan=2,
                                                            sticky="w", pady=(6, 0))
            r += 1
            ttk.Separator(frm).grid(row=r, column=0, columnspan=4, sticky="ew", pady=10)
            r += 1

        ttk.Label(frm, text="Optional, per phase — unset means TOPilot decides",
                  foreground="grey").grid(row=r, column=0, columnspan=4, sticky="w",
                                          pady=(0, 6))
        r += 1

        ttk.Label(frm, text="Preferred orientation").grid(row=r, column=0, sticky="w")
        self.po = TriState(frm, [("None", "none"),
                                 ("March-Dollase", "march_dollase"),
                                 ("Spherical harmonics", "spherical_harmonics")], width=22)
        self.po.set_value(s.get("po"))
        self.po.grid(row=r, column=1, sticky="w", padx=(6, 0))
        self.po.bind("<<ComboboxSelected>>", lambda *_: self._sync_po())
        ttk.Label(frm, text="order").grid(row=r, column=2, sticky="e", padx=(8, 2))
        self.po_order = ttk.Combobox(frm, values=["2", "4", "8"], width=4, state="readonly")
        self.po_order.set(str(s.get("po_order", cfg["phases"]["po_order"])))
        self.po_order.grid(row=r, column=3, sticky="w")
        r += 1

        ttk.Label(frm, text="Anisotropic broadening").grid(row=r, column=0, sticky="w",
                                                           pady=(6, 0))
        self.aniso = TriState(frm, [("Stephens (by crystal system)", "stephens")], width=22)
        self.aniso.set_value(s.get("anisotropic"))
        self.aniso.grid(row=r, column=1, sticky="w", padx=(6, 0), pady=(6, 0))
        Tooltip(self.aniso, "Stephens anisotropic broadening. Left unset deliberately — "
                            "add it when the difference plot shows specific reflection "
                            "classes misfitting while others fit well.")
        r += 1

        self.beq_by_type = TriState(frm, [("Yes", True), ("No", False)], width=22)
        self.beq_by_type.set_value(s.get("beq_by_type"))
        ttk.Label(frm, text="beq by site type").grid(row=r, column=0, sticky="w", pady=(6, 0))
        self.beq_by_type.grid(row=r, column=1, sticky="w", padx=(6, 0), pady=(6, 0))
        r += 1

        self.pawley_note = ttk.Label(frm, foreground="grey", wraplength=430,
                                     justify="left", text="")
        self.pawley_note.grid(row=r, column=0, columnspan=4, sticky="w", pady=(8, 0))
        r += 1

        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=4, sticky="e", pady=(14, 0))
        ttk.Button(btns, text="OK", command=self._ok).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=(0, 6))

        self._sync_po()
        self._sync_pawley_options()
        self.bind("<Return>", lambda _e: self._ok())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.grab_set()
        if self.is_pawley:
            self.cellsym.sg_box.focus_set()

    def _sync_po(self):
        state = "readonly" if self.po.value() == "spherical_harmonics" else "disabled"
        self.po_order.configure(state=state)
        if self.is_pawley:
            self.po_order.configure(state="disabled")

    def _sync_pawley_options(self):
        """Grey what a Pawley phase cannot use: PO (its intensities are already
        free, so nothing is left to correct) and beq-by-type (no sites).
        Anisotropic broadening stays -- it acts on widths, which stay fixed."""
        if not self.is_pawley:
            return
        for widget in (self.po, self.po_order, self.beq_by_type):
            widget.configure(state="disabled")
        self.pawley_note.configure(
            text="Preferred orientation and beq-by-type do not apply to a Pawley "
                 "phase — its intensities are free and it has no sites.")

    def _ok(self):
        s = dict(self.row.settings)
        if self.is_pawley:
            s.update(self.cellsym.value())
            s["refine_cell"] = self.refine_cell.get()
        if self.is_pawley:
            s["po"] = s["po_order"] = s["beq_by_type"] = None
        else:
            s["po"] = self.po.value()
            s["po_order"] = (int(self.po_order.get())
                             if self.po.value() == "spherical_harmonics" else None)
            s["beq_by_type"] = self.beq_by_type.value()
        s["anisotropic"] = self.aniso.value()
        self.row.settings = s
        self.row.refresh_summary()
        self.result = s
        self.destroy()


class PhaseRow(ttk.Frame):
    SOURCES = [("CIF", "cif"), (".str file", "str"), ("Pawley (hkl_Is)", "pawley")]

    def __init__(self, parent, owner):
        super().__init__(parent)
        self.owner = owner
        self.settings: dict = {}

        self.source_var = tk.StringVar(value="cif")
        box = ttk.Combobox(self, width=14, state="readonly",
                           values=[lbl for lbl, _ in self.SOURCES])
        box.set("CIF")
        box.grid(row=0, column=0, padx=(0, 4))
        box.bind("<<ComboboxSelected>>",
                 lambda _e: self._set_source(dict((l, v) for l, v in self.SOURCES)[box.get()]))
        self.source_box = box

        self.path_var = tk.StringVar()
        # Naming a structure is what switches the inferred Peak Fit / Solve
        # stages off, so the rule has to see the path change, not just the row.
        self.path_var.trace_add("write", lambda *_: owner._sync_inferred_stages())
        self.path_entry = ttk.Entry(self, textvariable=self.path_var, width=30)
        self.path_entry.grid(row=0, column=1, padx=(0, 2))
        self.browse_btn = ttk.Button(self, text="Browse…", width=9, command=self._browse)
        self.browse_btn.grid(row=0, column=2, padx=(0, 6))
        # Shown in place of the path box for a Pawley phase, which has no file.
        self.no_file_lbl = ttk.Label(self, foreground="grey", width=41,
                                     text="no file — cell and symmetry go in Options")

        self.name_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.name_var, width=16).grid(row=0, column=3, padx=(0, 6))

        self.definite = tk.BooleanVar(
            value=owner.cfg.get("phases", {}).get("confidence", "definite") == "definite")
        definite_box = ttk.Checkbutton(self, text="Definite", variable=self.definite)
        definite_box.grid(row=0, column=4)
        Tooltip(definite_box, "Will always be in model, untick for elimination "
                              "in quantitative work.")

        self.more_btn = ttk.Button(self, text="Options…", width=14, command=self._more)
        self.more_btn.grid(row=0, column=5, padx=(6, 2))
        Tooltip(self.more_btn, "Per-phase settings: Pawley cell and space group, "
                               "preferred orientation, anisotropic broadening, beq by type.")

        ttk.Button(self, text="✕", width=3,
                   command=lambda: owner.remove_row(self)).grid(row=0, column=6)

        self.summary = ttk.Label(self, text="", foreground="grey")
        self.summary.grid(row=1, column=0, columnspan=7, sticky="w", pady=(0, 4))
        self._summary_on = True
        self.refresh_summary()

    def _set_source(self, value):
        self.source_var.set(value)
        pawley = value == "pawley"
        if pawley:
            self.path_entry.grid_remove()
            self.browse_btn.grid_remove()
            self.no_file_lbl.grid(row=0, column=1, columnspan=2, sticky="w", padx=(0, 6))
            if not self.name_var.get():
                self.name_var.set("pawley_phase")
        else:
            self.no_file_lbl.grid_remove()
            self.path_entry.grid(row=0, column=1, padx=(0, 2))
            self.browse_btn.grid(row=0, column=2, padx=(0, 6))
            self.path_entry.configure(state="normal")
            self.browse_btn.configure(state="normal")
        self.refresh_summary()
        self.owner._sync_inferred_stages()
        self.owner.validate()

    def _browse(self):
        kinds = ([("CIF files", "*.cif"), ("All files", "*.*")]
                 if self.source_var.get() == "cif"
                 else [("STR files", "*.str *.txt"), ("All files", "*.*")])
        path = filedialog.askopenfilename(title="Choose a structure file",
                                          initialdir=self.owner.last_dir(),
                                          filetypes=kinds)
        if path:
            self.owner._remember_dir(path)
            self.path_var.set(path)
            if not self.name_var.get():
                self.name_var.set(Path(path).stem)
            self.owner.validate()

    def _more(self):
        dlg = PhaseSettingsDialog(self.winfo_toplevel(), self,
                                  self.owner.space_groups, self.owner.cfg)
        self.wait_window(dlg)
        self.owner._sync_inferred_stages()      # a Pawley cell counts too
        self.owner.validate()

    def refresh_summary(self):
        # Warn on the button only when the missing thing lives behind it: a
        # CIF row with no file is fixed by Browse, not by Options.
        if self.source_var.get() != "pawley":
            self.more_btn.configure(text="Options…", style="TButton")
        elif self.problems():
            self.more_btn.configure(text="⚠  Set cell…", style="Warn.TButton")
        else:
            self.more_btn.configure(text="Cell + options…", style="TButton")

        bits = []
        s = self.settings
        if self.source_var.get() == "pawley":
            sg = s.get("space_group")
            bits.append(f"space group {sg}" if sg else "space group NOT SET")
            cell = s.get("cell") or {}
            if cell.get("a") is None:
                bits.append("cell NOT SET")
            else:
                bits.append("a=%.4f" % cell["a"])
        if s.get("po"):
            bits.append(f"PO {s['po']}" + (f" order {s['po_order']}" if s.get("po_order") else ""))
        if s.get("anisotropic"):
            bits.append(s["anisotropic"])
        if s.get("beq_by_type") is not None:
            bits.append(f"beq by type: {'yes' if s['beq_by_type'] else 'no'}")
        text = ("      " + " · ".join(bits)) if bits else ""
        self.summary.configure(text=text)
        # A summary with nothing to say must not hold its line open: an empty
        # label is still a line high, which put the best part of a blank row
        # between one phase and the next. Only touch grid when the state
        # actually flips -- validate() calls this on every keystroke.
        if bool(text) != self._summary_on:
            self._summary_on = bool(text)
            (self.summary.grid if self._summary_on else self.summary.grid_remove)()

    def is_blank(self) -> bool:
        """True for a row nobody has touched: still the default CIF source,
        no path, no name. The wizard always seeds one such row, and adding
        another leaves the first one behind -- neither should have to be
        filled in or deleted just because Solve or Peak Fit/Index is already
        supplying the structure."""
        return (self.source_var.get() == "cif" and not self.path_var.get().strip()
                and not self.name_var.get().strip())

    def problems(self) -> list[str]:
        """Reasons OK stays disabled; also drives the Options button label.
        Paths and required Pawley fields only -- no physics validation."""
        out = []
        name = self.name_var.get().strip() or "(unnamed phase)"
        src = self.source_var.get()
        if src in ("cif", "str"):
            p = self.path_var.get().strip()
            if not p:
                out.append(f"{name}: none chosen")
            elif not Path(p).is_file():
                out.append(f"{name}: file does not exist")
        else:
            s = self.settings
            if not s.get("space_group"):
                out.append(f"{name}: Pawley phase has no space group")
            cell = s.get("cell") or {}
            _, free = derive_cell(s.get("crystal_system", ""), {})
            missing = [k for k in free if cell.get(k) is None]
            if missing:
                out.append(f"{name}: Pawley cell missing {', '.join(missing)}")
        return out

    def to_dict(self) -> dict:
        src = self.source_var.get()
        d = {
            "source": src,
            "path": as_posix(self.path_var.get().strip()) if src != "pawley" else None,
            # A fallback name here used to write a fake "phase" into the job
            # file for an untouched row -- is_blank() then read that name back
            # on the next load as something the user had typed, so the row
            # never counted as blank again. Leave it empty; "(unnamed phase)"
            # is a display-only fallback (problems(), refresh_summary()).
            "name": self.name_var.get().strip(),
            "confidence": "definite" if self.definite.get() else "maybe",
        }
        s = self.settings
        if src == "pawley":
            d["space_group"] = s.get("space_group")
            d["crystal_system"] = s.get("crystal_system")
            d["cell"] = s.get("cell")
            d["refine_cell"] = s.get("refine_cell", True)
        # Unset per-phase options are omitted, never written as null.
        for key in ("po", "po_order", "anisotropic", "beq_by_type"):
            if s.get(key) is not None:
                d[key] = s[key]
        return d

    def from_dict(self, d: dict):
        label = {v: l for l, v in self.SOURCES}.get(d.get("source", "cif"), "CIF")
        self.source_box.set(label)
        self._set_source(d.get("source", "cif"))
        self.path_var.set(d.get("path") or "")
        self.name_var.set(d.get("name") or "")
        self.definite.set(d.get("confidence", "definite") == "definite")
        self.settings = {k: d[k] for k in
                         ("space_group", "crystal_system", "cell", "refine_cell",
                          "po", "po_order", "anisotropic", "beq_by_type") if k in d}
        self.refresh_summary()


# --------------------------------------------------------------------------
# The wizard
# --------------------------------------------------------------------------

class Wizard(tk.Tk):
    def __init__(self, out_override: str | None, workflow: str,
                 from_claude: bool = True):
        super().__init__()
        self.exit_code = EXIT_CANCEL
        self.out_override = out_override
        self.workflow = workflow
        self.from_claude = from_claude
        self.job_path: Path | None = None

        self.warnings: list[str] = []
        # Analyses the user has hand-toggled; _sync_inferred_stages leaves these
        # alone for the rest of the session.
        self._auto_latched: set[str] = set()
        self.cfg = load_config(self.warnings)
        self._last_dir = self.cfg.get("general", {}).get("last_dir", "")
        # Folder the output .inp was last written to; overrides the data's own
        # folder when naming a new job -- but only once THIS session has
        # pointed output there itself (Browse, or naming a job to load), not
        # merely because it's what config remembers from a previous, likely
        # unrelated, dataset. Without _out_dir_pinned, picking a brand new
        # data file kept silently landing the output in yesterday's folder.
        self._out_dir = self.cfg.get("general", {}).get("out_dir", "")
        self._out_dir_pinned = False
        self.instruments = load_instruments(self.warnings)
        self.space_groups = load_space_groups(self.warnings)
        self.hovertext = load_hovertext()

        self.title("TOPilot wizard  "
                   "[enter compulsory items; non-compulsory can be left to TOPilot]")
        self._style()
        self._build()
        # --workflow picks the opening analysis instead of the opening tab.
        if self.workflow:
            key = "peak_fitting" if self.workflow.startswith("peak") else self.workflow
            if key in self.analysis and key != "rietveld":
                self.analysis["rietveld"].set(False)
                self.analysis[key].set(True)
        self._sync_analyses()
        self._apply_config()      # TOML/local assertions
        self._prefill()           # last job wins over them
        self.validate()

        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.bind("<Return>", lambda _e: self.on_ok())
        self.bind("<Escape>", lambda _e: self.on_cancel())
        # The watchdog releases a Claude Code call blocked on this process.
        # Standalone, nothing is waiting, so there is no auto-close.
        if self.from_claude:
            self.after(WATCHDOG_MS, self.on_timeout)
        self._fit_to_screen()
        self._raise_window()

    def _fit_to_screen(self):
        """Open no taller than the work area of the screen we are actually on.

        Two traps: the taskbar is not part of the work area, so clamping to
        screenheight still overflows; and winfo_screenheight() reports the
        PRIMARY display, so a window opened on a larger secondary monitor must
        not be squeezed into the smaller one's work area.
        """
        self.update_idletasks()
        avail = self._work_area_height()
        bar_h = self._btn_bar.winfo_reqheight()
        body_h = self._scroll.body_height()

        # The scroller shows as much of the form as the screen allows; the rest
        # scrolls. The button bar is outside it and always visible.
        view = max(240, min(body_h, avail - bar_h))
        self._scroll.set_view_height(view)
        self.update_idletasks()
        width = max(self._scroll.body.winfo_reqwidth() + 24, 640)
        self.geometry(f"{width}x{view + bar_h}")
        self.minsize(600, min(360, avail))

    def _work_area_height(self) -> int:
        """Work area of the monitor the window sits on, less a margin for the
        title bar. Falls back to Tk's primary-screen figure off Windows."""
        try:
            import ctypes
            from ctypes import wintypes

            class RECT(ctypes.Structure):
                _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG),
                            ("right", wintypes.LONG), ("bottom", wintypes.LONG)]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                            ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]

            user32 = ctypes.windll.user32
            mon = user32.MonitorFromWindow(self.winfo_id(), 2)   # NEAREST
            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(mon, ctypes.byref(info)):
                return max(400, info.rcWork.bottom - info.rcWork.top - 40)
        except Exception:
            pass
        return max(400, int(self.winfo_screenheight() * 0.90))

    # -- appearance --------------------------------------------------------
    def _style(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        self.option_add("*Font", "{Segoe UI} 9")
        style.configure(".", font=("Segoe UI", 9))

        # Sections 3 and 4 are separate frames, so their label columns size
        # themselves independently and their entry boxes come out different
        # widths. Give both the same floor, measured from the widest label in
        # either -- measured rather than hard-coded so it follows the DPI.
        self._label_col = tkfont.Font(font=("Segoe UI", 9)).measure(
            "Variable slits *") + 12
        style.configure("Head.TLabel", font=("Segoe UI", 9, "bold"))
        style.configure("Warn.TButton", foreground="#a03000")
        style.configure("Req.TLabel", foreground="#9c3524")
        style.configure("TNotebook.Tab", padding=(12, 4),
                        font=("Segoe UI", 9))
        # ttk matches these in order, so "disabled" must precede "!selected" or
        # an unticked tab would take the plain unselected grey instead.
        style.map("TNotebook.Tab",
                  font=[("selected", ("Segoe UI", 9, "bold"))],
                  foreground=[("disabled", "#c2c9d1"),
                              ("selected", "#1a2530"),
                              ("!selected", "#6b7783")])

        # Native themes draw LabelFrame borders themselves and ignore
        # bordercolor, so borrow clam's element for this one style.
        try:
            style.element_create("Section.border", "from", "clam", "border")
            style.layout("Section.TLabelframe", [
                ("Section.border", {"sticky": "nswe", "children": [
                    ("Labelframe.padding", {"sticky": "nswe"})]})])
        except tk.TclError:
            pass                      # element already exists, or clam missing
        style.configure("Section.TLabelframe", borderwidth=2, relief="solid",
                        bordercolor="#a3aebb", lightcolor="#a3aebb",
                        darkcolor="#a3aebb")
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 9, "bold"),
                        foreground="#33414f")

        # An analysis the FORM turned on is marked by GREY LABEL TEXT, not by a
        # recoloured tick: Vista draws its indicator from a fixed bitmap and
        # ignores colour.
        style.configure("Auto.TCheckbutton", foreground="#8d97a2")
        self.auto_check_style = "Auto.TCheckbutton"

    def _raise_window(self):
        """The window opens behind VS Code. Lift, force topmost, then release —
        staying topmost would make every file browser fight it."""
        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.focus_force()

    # -- layout ------------------------------------------------------------
    def _build(self):
        """Rows, top to bottom:
             0  analysis type       shared   -- 1 which analyses to run
             1  extra instructions  shared   -- 2 Non-standard instructions
             2  measurement frame   shared   -- 3 The measurement
             3  job frame           shared   -- 4 What to do with it
             4  notebook            per-tab  -- 5 The analysis task(s)
             5  warnings
             6  status + buttons

        Everything shared comes FIRST, and the notebook last: the shared blocks
        are short and fixed-height, and the notebook is the one region that
        grows, so expanding an optional group pushes against the button bar
        alone.

        Rows 0-5 sit inside ONE outer scroller and the button bar stays outside
        it, so OK can never scroll away. Do not nest another scroller inside
        it -- that clips content instead of scrolling it.

        Row 4 carries the weight so the notebook takes any SPARE height on a
        large screen. If a section is ever inserted above it, this number must
        move with it.
        """
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._scroll = Scrollable(self)
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._host = self._scroll.body
        self._host.columnconfigure(0, weight=1)
        self._host.rowconfigure(4, weight=1)

        self._build_analysis_type()    # shared, gates the tabs below
        self._build_extra()            # shared, above the notebook
        self._build_measurement()      # shared, above the notebook
        self._build_job()              # shared, above the notebook
        self._build_notebook()         # per-workflow, last
        self._build_buttons()

        if self.warnings:
            bar = ttk.Label(self._host, text="⚠  " + "  |  ".join(self.warnings),
                            foreground="#a05000", wraplength=880)
            bar.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 6))

    def _build_analysis_type(self):
        """One checkbox per analysis tab. Future has none -- it is a notice
        board, not work."""
        f = ttk.LabelFrame(self._host, text=" 1 · Analysis type (select a combination) ",
                           style="Section.TLabelframe", padding=(10, 6))
        f.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))
        box = ttk.Frame(f)
        box.pack(fill="x")

        self.analysis: dict[str, tk.BooleanVar] = {}
        self.analysis_boxes: dict[str, ttk.Checkbutton] = {}
        for key, label in ANALYSES:
            var = tk.BooleanVar(value=(key == "rietveld"))   # Riet is the default
            cb = ttk.Checkbutton(box, text=label.strip(), variable=var,
                                 command=lambda k=key: self._on_analysis_clicked(k))
            if key in ("peak_fitting", "solve"):
                cb.configure(style=self.auto_check_style)
            # A Tooltip is bound at construction, so this text cannot depend
            # on the current state.
            Tooltip(cb, "Black label if you activated it yourself.  Grey label "
                        "if TOPilot switched it on to meet your other choices.")
            cb.pack(side="left", padx=(0, 14))
            self.analysis[key], self.analysis_boxes[key] = var, cb

        self.analysis_note = ttk.Label(f, foreground="grey", wraplength=640,
                                       justify="left", text="")
        self.analysis_note.pack(fill="x", pady=(4, 0))
        wrap_to_width(self.analysis_note)

    def _build_extra(self):
        """Free-text notes: one widget above the tab strip, shared by every tab.
        A copy per tab would be N widgets that can disagree."""
        f = ttk.LabelFrame(self._host,
                           text=" 2 · Non-standard additional text instructions for TOPilot ",
                           style="Section.TLabelframe", padding=(10, 6))
        f.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        f.columnconfigure(0, weight=1)
        self.extra = tk.Text(f, height=2, wrap="word", font=("Segoe UI", 9))
        self.extra.grid(row=0, column=0, sticky="ew")
        Tooltip(self.extra, "Enter any specific instructions for the AI as free text.  "
                            "This can normally be left blank.")

    def _build_measurement(self):
        """Data file, instrument, wavelength, slits. Parented to root, not a tab:
        every workflow shares these by construction."""
        f = ttk.LabelFrame(self._host, text=" 3 · Data and refinement controls ",
                           style="Section.TLabelframe", padding=(10, 6))
        f.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))
        # The fields take three quarters of the spare width and an empty column
        # takes the rest, so a full-width window does not stretch a path box
        # right across the form. Section 4 repeats all three settings so its
        # output box comes out the same width as these.
        #
        # The spacer must exist as a widget -- grid gives a column a weight
        # only while something occupies it -- and it must sit on a row of its
        # own, because a weight is shared out only ABOVE each column's natural
        # width. Anything wide left in column 1 (the radio rows, the wavelength
        # note) raises that natural width and the two sections drift apart
        # again, so those span the spacer column instead.
        f.columnconfigure(0, minsize=self._label_col)
        f.columnconfigure(1, weight=3, minsize=FIELD_COL_MIN)
        f.columnconfigure(3, weight=1)
        ttk.Frame(f).grid(row=99, column=3, sticky="ew")

        # Three ways in. Directory and list mode both mean many datasets, which
        # is what Seq/Para exists for.
        ttk.Label(f, text="Data is").grid(row=0, column=0, sticky="w")
        self.data_mode = tk.StringVar(value="file")
        modes = ttk.Frame(f)
        modes.grid(row=0, column=1, columnspan=3, sticky="w", padx=6)
        for label, value in (("One file", "file"),
                             ("A folder of files", "dir"),
                             ("A list of files", "list")):
            rb = ttk.Radiobutton(modes, text=label, variable=self.data_mode,
                                 value=value, command=self._on_data_mode)
            rb.pack(side="left", padx=(0, 12))
            if value == "list":
                Tooltip(rb, "Typically a file containing filenames and metadata "
                            "with column headings and an optional "
                            "colon-separated list of cif files.")

        self.data_label = req(f, "Data file")
        self.data_label.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.data_var = tk.StringVar()
        self.data_var.trace_add("write", lambda *_: self._on_data_changed())
        ttk.Entry(f, textvariable=self.data_var).grid(row=1, column=1, sticky="ew",
                                                      padx=6, pady=(6, 0))
        ttk.Button(f, text="Browse…", command=self._browse_data).grid(row=1, column=2,
                                                                       pady=(6, 0))
        self.data_note = ttk.Label(f, text="", foreground="grey")
        self.data_note.grid(row=2, column=1, sticky="w", padx=6)
        self.data_note.grid_remove()          # shown only once it has a count
        self._data_note_on = False

        req(f, "Instrument").grid(row=3, column=0, sticky="w", pady=(6, 0))
        # "None specified" omits the instrument key entirely, which under this
        # form's contract means "you decide". Placeholder first: never default
        # to a real instrument, or inattention silently asserts its LP factor
        # and emission line.
        self.instr_box = ttk.Combobox(
            f, state="readonly",
            values=[PICK_INSTRUMENT] + [i["name"] for i in self.instruments]
                   + [NO_INSTRUMENT])
        self.instr_box.grid(row=3, column=1, sticky="ew", padx=6, pady=(6, 0))
        self.instr_box.bind("<<ComboboxSelected>>", lambda _e: self._on_instrument())
        self.instr_box.set(PICK_INSTRUMENT)

        # The star appears only while the field is REQUIRED -- i.e. the chosen
        # instrument has no emission line of its own.
        self.wl_label = req(f, "Wavelength")
        self.wl_label.grid(row=4, column=0, sticky="w", pady=(6, 0))
        self.wl_text = self.wl_label.winfo_children()[0]
        self.wl_star = self.wl_label.winfo_children()[1]
        self.wl_star.pack_forget()
        wl = ttk.Frame(f)
        wl.grid(row=4, column=1, columnspan=3, sticky="ew", padx=6, pady=(6, 0))
        self.wl_var = tk.StringVar()
        self.wl_var.trace_add("write", lambda *_: self.validate())
        self.wl_entry = ttk.Entry(wl, textvariable=self.wl_var, width=14)
        self.wl_entry.pack(side="left")
        self.wl_note = ttk.Label(wl, text="", foreground="grey")
        self.wl_note.pack(side="left", padx=(8, 0))

        self.slits_label = req(f, "Variable slits")
        self.slits_label.grid(row=5, column=0, sticky="w", pady=(6, 0))
        self.slits = TriState(f, [("Fixed slits", "fixed"),
                                  ("Variable slits", "variable")], width=24)
        self.slits.grid(row=5, column=1, sticky="w", padx=6, pady=(6, 0))
        Tooltip(self.slits, "Select slit type.  TOPilot will attempt to determine "
                            "this if not specified.")

        # iters, continue_after_convergence and do_errors mean the same thing in
        # every workflow, so they live here rather than in one tab's panel.
        g = CollapsibleGroup(f, "Refinement controls (optional)")
        g.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        b = g.body

        ttk.Label(b, text="iters").grid(row=0, column=0, sticky="w")
        self.iters = ttk.Entry(b, width=8)
        self.iters.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.iters_note = ttk.Label(b, text="", foreground="grey")
        self.iters_note.grid(row=0, column=2, sticky="w", padx=(6, 0))

        ttk.Label(b, text="continue_after_convergence").grid(row=1, column=0,
                                                             sticky="w", pady=(6, 0))
        self.cac = yes_no(b, width=16)
        self.cac.grid(row=1, column=1, columnspan=2, sticky="w", padx=(6, 0), pady=(6, 0))

        ttk.Label(b, text="do_errors").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.do_errors = yes_no(b, width=16)
        self.do_errors.grid(row=2, column=1, columnspan=2, sticky="w",
                            padx=(6, 0), pady=(6, 0))
        Tooltip(self.do_errors, "Left unset, TOPilot enables it when esds matter — "
                                "on a converged cycle and at the end.")

    def _build_notebook(self):
        """Workflow tabs. Everything shared sits outside, so a new tab adds only
        its own fields."""
        wrap = ttk.LabelFrame(self._host,
                              text=" 5 · The analysis task(s) (fill one or several tabs) ",
                              style="Section.TLabelframe", padding=(8, 4))
        wrap.grid(row=4, column=0, sticky="nsew", padx=12, pady=(0, 4))
        wrap.columnconfigure(0, weight=1)
        wrap.rowconfigure(0, weight=1)

        self.nb = ttk.Notebook(wrap)
        self.nb.grid(row=0, column=0, sticky="nsew")
        self.nb.bind("<<NotebookTabChanged>>", lambda _e: self._on_tab_changed())

        # ttk has no per-tab foreground -- every tab in one Notebook is styled
        # uniformly by STATE (selected/disabled), never by tab identity -- so
        # "this tab still needs something" cannot be shown by colouring its
        # label. A small hand-drawn icon stands in for that channel instead;
        # kept as an attribute or Tk would garbage-collect it off every tab
        # the moment this method returns.
        self._tab_flag_icon = self._make_tab_flag_icon()

        # Built in ANALYSES order. self.tabs maps each key to its frame: with
        # tabs enabled and disabled under it, an index means nothing.
        self.tabs: dict[str, ttk.Frame] = {}
        self._build_peakfit_tab()
        self._build_solve_tab()
        self._build_rietveld_tab()
        self._build_pdf_tab()
        self._build_seqpara_tab()
        self._build_future_tab()

    @staticmethod
    def _make_tab_flag_icon() -> tk.PhotoImage:
        """A tiny sparkle, hand-drawn rather than text so it needs no font
        fallback and reads the same on every theme. Same muted red as the
        '* required' asterisk, since it marks the same thing: something
        required is still missing, just on a tab instead of a field."""
        img = tk.PhotoImage(width=9, height=9)
        color = "#9c3524"
        for x, y in ((4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7),
                     (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4),
                     (3, 3), (5, 3), (3, 5), (5, 5)):
            img.put(color, (x, y))
        return img

    def _sync_tab_flags(self, tab_problems: dict[str, list[str]]):
        """Flag a ticked tab that validate() found something missing on.
        tab_problems carries only the tabs it actually checked, so anything
        else -- unticked, or PDF/Seq/Para/Future which have no required
        fields of their own -- always clears."""
        if not hasattr(self, "tabs"):
            return
        for key, _ in ANALYSES:
            if key not in self.tabs:
                continue
            flagged = bool(tab_problems.get(key))
            self.nb.tab(self.tabs[key],
                       image=self._tab_flag_icon if flagged else "",
                       compound="right" if flagged else "none")

    def _build_rietveld_tab(self):
        outer = ttk.Frame(self.nb, padding=(4, 4))
        self.nb.add(outer, text=dict(ANALYSES)["rietveld"])
        self.tabs["rietveld"] = outer
        outer.columnconfigure(0, weight=1)
        # No scroller of its own: the whole form scrolls (see _build).
        tab = ttk.Frame(outer, padding=(6, 4))
        tab.grid(row=0, column=0, sticky="nsew")
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        # --- required: rule set + phases
        top = ttk.Frame(tab)
        top.grid(row=0, column=0, sticky="ew")
        ttk.Label(top, text="Rule set", style="Head.TLabel").pack(side="left")
        self.rules = tk.StringVar(value=self.cfg["rietveld"]["rules"])
        ttk.Radiobutton(top, text="Rietveld/Pawley", variable=self.rules,
                        value="rietveld").pack(side="left", padx=(10, 4))
        ttk.Radiobutton(top, text="Quantitative phase analysis", variable=self.rules,
                        value="quantitative").pack(side="left")

        ph = ttk.LabelFrame(tab, text="Phases", padding=(8, 6))
        ph.grid(row=1, column=0, sticky="nsew", pady=(8, 6))
        ph.columnconfigure(0, weight=1)
        hdr = ttk.Frame(ph)
        hdr.grid(row=0, column=0, sticky="w")
        for text, width in (("Source", 16), ("File", 43), ("Name", 18), ("", 10)):
            ttk.Label(hdr, text=text, width=width, foreground="grey").pack(side="left")
        self.phase_host = ttk.Frame(ph)
        self.phase_host.grid(row=1, column=0, sticky="ew")
        self.phase_rows: list[PhaseRow] = []
        ttk.Button(ph, text="+  Add phase", command=self.add_phase_row).grid(
            row=2, column=0, sticky="w", pady=(6, 0))

        # --- optional: three collapsible groups, all closed
        opt = ttk.LabelFrame(tab, text="Optional — TOPilot decides if unset",
                             padding=(8, 6))
        opt.grid(row=2, column=0, sticky="ew")
        opt.columnconfigure(0, weight=1)
        self._build_optional(opt)

    def _build_peakfit_tab(self):
        """A four-stage pipeline: peak search -> peak fit -> index -> Pawley.
        Every stage is optional, so each sits in a collapsible group."""
        outer = ttk.Frame(self.nb, padding=(4, 4))
        self.nb.add(outer, text=dict(ANALYSES)["peak_fitting"])
        self.tabs["peak_fitting"] = outer
        outer.columnconfigure(0, weight=1)
        # No scroller of its own: the whole form scrolls (see _build).
        tab = ttk.Frame(outer, padding=(6, 4))
        tab.grid(row=0, column=0, sticky="nsew")
        tab.columnconfigure(0, weight=1)

        panel = ttk.LabelFrame(
            tab, text="Analysis stages (a default TOPilot protocol is already set)",
            padding=(8, 6))
        panel.grid(row=0, column=0, sticky="ew")
        panel.columnconfigure(0, weight=1)
        ttk.Label(panel, foreground="grey", justify="left",
                  text="All four stages run by default — open one only to change "
                       "it.").grid(row=0, column=0, sticky="w", pady=(0, 4))

        # --- 1 peak search --------------------------------------------------
        g1 = CollapsibleGroup(panel, "1 · Peak search")
        g1.grid(row=1, column=0, sticky="ew")
        b1 = g1.body
        ttk.Label(b1, text="Method").grid(row=0, column=0, sticky="w")
        self.pf_method = ttk.Combobox(b1, state="readonly", width=34,
                                      values=[PF_METHOD_DEFAULT,
                                              "Default peak search (skill decides)",
                                              "Paste a list of 2θ values"])
        self.pf_method.current(0)
        self.pf_method.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.pf_method.bind("<<ComboboxSelected>>", lambda _e: self._sync_peakfit())
        self.pf_list = tk.Text(b1, height=5, wrap="word", font=("Consolas", 9))
        self.pf_list.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        Tooltip(self.pf_list, "One 2θ value per line, or separated by spaces or "
                              "commas. Paste straight from a peak-search result.")
        bind_text_revalidate(self.pf_list, self.validate)

        # --- 2 peak fitting -------------------------------------------------
        g2 = CollapsibleGroup(panel, "2 · Peak fitting")
        g2.grid(row=2, column=0, sticky="ew")
        b2 = g2.body
        self.pf_fit = tk.BooleanVar(value=True)
        ttk.Checkbutton(b2, text="Fit the peaks to optimise positions and widths",
                        variable=self.pf_fit,
                        command=self._sync_peakfit).grid(row=0, column=0,
                                                         columnspan=2, sticky="w")
        ttk.Label(b2, text="Peak shape").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.pf_peak_shape = TriState(b2, PEAK_SHAPES_PEAKFIT, width=34)
        self.pf_peak_shape.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=(4, 0))
        self.pf_refine_axial = tk.BooleanVar(value=True)
        ttk.Checkbutton(b2, text="Refine Simple_Axial_Model()",
                        variable=self.pf_refine_axial).grid(row=2, column=0,
                                                            columnspan=2, sticky="w",
                                                            pady=(4, 0))

        # --- 3 indexing -----------------------------------------------------
        g3 = CollapsibleGroup(panel, "3 · Indexing")
        g3.grid(row=3, column=0, sticky="ew")
        b3 = g3.body
        self.pf_index = tk.BooleanVar(value=True)
        ttk.Checkbutton(b3, text="Index the peak list", variable=self.pf_index,
                        command=self._sync_peakfit).grid(row=0, column=0,
                                                         columnspan=3, sticky="w")
        ttk.Label(b3, text="Include peaks down to").grid(row=1, column=0, sticky="w",
                                                         pady=(4, 0))
        self.pf_min_pct = ttk.Entry(b3, width=6)
        self.pf_min_pct.grid(row=1, column=1, sticky="w", padx=(6, 2), pady=(4, 0))
        ttk.Label(b3, text="% of the strongest (blank = skill decides)", foreground="grey").grid(
            row=1, column=2, sticky="w", pady=(4, 0))

        # --- 4 Pawley -------------------------------------------------------
        g4 = CollapsibleGroup(panel, "4 · Pawley check")
        g4.grid(row=4, column=0, sticky="ew")
        b4 = g4.body
        self.pf_pawley = tk.BooleanVar(value=True)
        ttk.Checkbutton(b4, text="Pawley-fit the best indexing solutions",
                        variable=self.pf_pawley,
                        command=self._sync_peakfit).grid(row=0, column=0,
                                                         columnspan=3, sticky="w")
        ttk.Label(b4, text="Top").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.pf_top_n = ttk.Entry(b4, width=6)
        self.pf_top_n.insert(0, "3")
        self.pf_top_n.grid(row=1, column=1, sticky="w", padx=(6, 2), pady=(4, 0))
        ttk.Label(b4, text="solutions", foreground="grey").grid(row=1, column=2,
                                                                sticky="w", pady=(4, 0))

        self._sync_peakfit()

    def _build_solve_tab(self):
        """Structure solution. Method comes first because it decides what the
        rest of the tab shows."""
        outer = ttk.Frame(self.nb, padding=(4, 4))
        self.nb.add(outer, text=dict(ANALYSES)["solve"])
        self.tabs["solve"] = outer
        outer.columnconfigure(0, weight=1)
        # No scroller of its own: the whole form scrolls (see _build).
        tab = ttk.Frame(outer, padding=(6, 4))
        tab.grid(row=0, column=0, sticky="nsew")
        tab.columnconfigure(0, weight=1)

        ttk.Label(tab, text="Method").grid(row=0, column=0, sticky="w")
        self.solve_method = tk.StringVar(value=SOLVE_METHODS[0][1])   # annealing
        meth = ttk.Frame(tab)
        meth.grid(row=1, column=0, sticky="w", pady=(2, 8))
        for label, value in SOLVE_METHODS:
            ttk.Radiobutton(meth, text=label, variable=self.solve_method, value=value,
                            command=self._sync_solve).pack(side="left", padx=(0, 14))

        self.solve_model = ttk.LabelFrame(tab, text=" Structure type ", padding=(8, 6))
        self.solve_model.grid(row=2, column=0, sticky="ew")
        self.solve_kind = tk.StringVar(value="extended")
        kinds = ttk.Frame(self.solve_model)
        kinds.pack(anchor="w")
        for label, value in (("Extended", "extended"), ("Molecular", "molecular")):
            ttk.Radiobutton(kinds, text=label, variable=self.solve_kind, value=value,
                            command=self._sync_solve).pack(side="left", padx=(0, 14))

        self.zmat_frame = ttk.Frame(self.solve_model)
        self.zmat_frame.pack(fill="x", pady=(6, 0))
        self.zmat_source = tk.StringVar(value="file")
        src = ttk.Frame(self.zmat_frame)
        src.pack(anchor="w")
        for label, value in (("Z-matrix from file", "file"),
                             ("Paste a Z-matrix / rigid body", "paste")):
            ttk.Radiobutton(src, text=label, variable=self.zmat_source, value=value,
                            command=self._sync_solve).pack(side="left", padx=(0, 14))
        self.zmat_pick = ttk.Frame(self.zmat_frame)
        self.zmat_pick.pack(fill="x", pady=(4, 0))
        self.zmat_path = tk.StringVar()
        self.zmat_path.trace_add("write", lambda *_: self.validate())
        self.zmat_entry = ttk.Entry(self.zmat_pick, textvariable=self.zmat_path)
        self.zmat_entry.pack(side="left", fill="x", expand=True)
        self.zmat_btn = ttk.Button(self.zmat_pick, text="Browse…",
                                   command=self._browse_zmatrix)
        self.zmat_btn.pack(side="left", padx=(6, 0))
        self.zmat_text = tk.Text(self.zmat_frame, height=5, wrap="none",
                                 font=("Consolas", 9))
        self.zmat_text.pack(fill="x", pady=(4, 0))
        bind_text_revalidate(self.zmat_text, self.validate)

        # Shared by charge flipping and by an extended anneal; a molecular
        # anneal takes its atoms from the z-matrix instead.
        self.contents_frame = ttk.Frame(tab)
        self.contents_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.contents_label = req(self.contents_frame, "Empirical formula")
        self.contents_label.pack(side="left")
        self.contents_var = tk.StringVar()
        self.contents_var.trace_add("write", lambda *_: self.validate())
        self.contents = ttk.Entry(self.contents_frame, width=22,   # matches sg_box
                                  textvariable=self.contents_var)
        self.contents.pack(side="left", padx=(6, 0))
        Tooltip(self.contents, "One formula unit, e.g. Pb S O4 — not multiplied "
                               "by Z. TOPilot works out Z if left blank below.")
        ttk.Label(self.contents_frame, text="  Z").pack(side="left")
        self.solve_z = ttk.Entry(self.contents_frame, width=4)
        self.solve_z.pack(side="left", padx=(4, 0))
        Tooltip(self.solve_z, "Number of formula units in cell (if known)")

        cellbox = ttk.LabelFrame(tab, text=" Cell and symmetry ", padding=(8, 6))
        cellbox.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.solve_cell = CellSymmetry(cellbox, self.space_groups)
        self.solve_cell.pack(anchor="w")
        self.solve_cell_note = ttk.Label(cellbox, foreground="grey", wraplength=620,
                                         justify="left", text="")
        self.solve_cell_note.pack(anchor="w", pady=(4, 0))
        wrap_to_width(self.solve_cell_note, margin=24)

        self._sync_solve()

    def _build_pdf_tab(self):
        """No fields yet -- a named tab with an honest note."""
        tab = ttk.Frame(self.nb, padding=(14, 12))
        self.nb.add(tab, text=dict(ANALYSES)["pdf"])
        self.tabs["pdf"] = tab
        ttk.Label(tab, style="Head.TLabel", text="For future development").pack(anchor="w")
        ttk.Label(tab, foreground="grey", justify="left", wraplength=620,
                  text="PDF generation from raw data and refinement against G(r). "
                       "The controls are not built yet — tick the box and describe "
                       "what you want in section 2, and TOPilot will work from "
                       "that.").pack(anchor="w", pady=(2, 0))

    def _build_seqpara_tab(self):
        """How a multi-dataset run is expressed. The file list comes from the
        data input in section 3, not from here."""
        tab = ttk.Frame(self.nb, padding=(14, 10))
        self.nb.add(tab, text=dict(ANALYSES)["seq_para"])
        self.tabs["seq_para"] = tab
        ttk.Label(tab, foreground="grey", justify="left",
                  text="Modifies the refinement — all datasets specified in section 3 will be analysed."
                  ).pack(anchor="w", pady=(0, 8))
        self.seq_mode = tk.StringVar(value=SEQ_MODES[0][1])
        for label, value in SEQ_MODES:
            ttk.Radiobutton(tab, text=label, variable=self.seq_mode,
                            value=value).pack(anchor="w", pady=1)

        self.seq_reel = tk.BooleanVar(value=False)
        ttk.Checkbutton(tab, text="Create Reel output",
                        variable=self.seq_reel).pack(anchor="w", pady=(10, 0))

        self.seq_note = ttk.Label(tab, foreground="grey", wraplength=640,
                                  justify="left", text="")
        self.seq_note.pack(anchor="w", pady=(8, 0))

    def _build_future_tab(self):
        tab = ttk.Frame(self.nb, padding=(14, 12))
        self.nb.add(tab, text="  Future  ")
        self.tabs["future"] = tab
        ttk.Label(tab, style="Head.TLabel", text="For future development").pack(anchor="w")

    def _browse_zmatrix(self):
        path = filedialog.askopenfilename(
            title="Choose the CIF holding the molecular fragment",
            initialdir=self.last_dir(),
            filetypes=[("CIF", "*.cif"), ("All files", "*.*")])
        if path:
            self._remember_dir(path)
            self.zmat_path.set(path)
        self.validate()

    def _sync_solve(self):
        """Charge flipping solves from the data with no structural model, so the
        extended/molecular choice does not apply to it and is hidden."""
        cf = self.solve_method.get() == "charge_flipping"
        if cf:
            self.solve_model.grid_remove()
        else:
            self.solve_model.grid()

        molecular = (not cf) and self.solve_kind.get() == "molecular"
        if molecular:
            self.zmat_frame.pack(fill="x", pady=(6, 0))
            if self.zmat_source.get() == "file":
                self.zmat_pick.pack(fill="x", pady=(4, 0))
                self.zmat_text.pack_forget()
            else:
                self.zmat_pick.pack_forget()
                self.zmat_text.configure(state="normal")
                self.zmat_text.pack(fill="x", pady=(4, 0))
        else:
            self.zmat_frame.pack_forget()

        # Cell contents: needed for charge flipping and for an extended anneal.
        if molecular:
            self.contents_frame.grid_remove()
        else:
            self.contents_frame.grid()

        # Always enterable: the indexed cell is a starting point the user may
        # want to override.
        from_index = bool(self.analysis["peak_fitting"].get()) if hasattr(
            self, "analysis") else False
        self.solve_cell_note.configure(
            text=("Leave blank to take the cell from the Peak Fit/Index stage, "
                  "or type one here to use it instead." if from_index else ""))
        self.validate()

    def _on_tab_changed(self):
        """The output name follows the ticked stages, not the visible tab."""
        self.validate()

    def _sync_peakfit(self):
        """Grey each stage's own settings when that stage is switched off, and
        the pasted-list box unless the list method is chosen."""
        self.pf_list.configure(
            state="normal" if self.pf_method.current() == 2 else "disabled")

        self.pf_peak_shape.configure(state="readonly" if self.pf_fit.get() else "disabled")
        for entry, on in ((self.pf_min_pct, self.pf_index.get()),
                          (self.pf_top_n, self.pf_pawley.get())):
            entry.configure(state="normal" if on else "disabled")
        self.validate()

    def peakfit_peaks(self) -> list[float]:
        """Parse the pasted 2θ list. Newlines, spaces or commas."""
        out = []
        for token in self.pf_list.get("1.0", "end").replace(",", " ").split():
            value = num_or_none(token)
            if value is not None:
                out.append(float(value))
        return out

    # -- analysis type -----------------------------------------------------
    def on(self, key: str) -> bool:
        """Is this analysis ticked? Never ask the notebook which tab is
        showing: the visible tab says nothing about what the job will run."""
        var = self.analysis.get(key) if hasattr(self, "analysis") else None
        return bool(var and var.get())

    def active_stages(self) -> list[str]:
        """The ticked stages in pipeline order. Seq/Para is excluded -- it is a
        modifier that wraps the refinement, not a stage that follows it."""
        return [k for k in STAGES if self.on(k)]

    def _on_analysis_clicked(self, key: str):
        """A hand click latches: from here on the form stops auto-managing this
        box, or _sync_inferred_stages would undo the user's choice."""
        if key in ("peak_fitting", "solve"):
            self._auto_latched.add(key)
            self._sync_check_styles()

        # PDF and the pattern analyses are mutually exclusive; the box just
        # ticked wins, in both directions. Neither side is ever greyed.
        if self.analysis[key].get():
            if key == "pdf":
                for other in PDF_EXCLUDES:
                    self.analysis[other].set(False)
            elif key in PDF_EXCLUDES:
                self.analysis["pdf"].set(False)

        # Riet coming back on is the RESET for the inferred-stage rule: it drops
        # the latches so Peak Fit and Solve can tick themselves grey again until
        # a phase is named. Nothing else clears them.
        if key == "rietveld" and self.analysis[key].get():
            self._auto_latched.difference_update(("peak_fitting", "solve"))
            self._sync_inferred_stages()

        self._sync_analyses()

    def _sync_analyses(self):
        """Enable each tab from its checkbox, apply the PDF exclusion and the
        Seq/Para precondition, and keep the selection on a live tab."""
        if not hasattr(self, "analysis") or not hasattr(self, "tabs"):
            return

        # The defensive net for the paths that set boxes WITHOUT a click:
        # prefill, the inferred-stage rule, the data-mode switch. A click is
        # resolved in _on_analysis_clicked. If both sides are on, the PATTERN
        # stages yield.
        pdf_on = self.on("pdf")
        if pdf_on:
            for key in PDF_EXCLUDES:
                self.analysis[key].set(False)
        for key, _ in ANALYSES:
            self.analysis_boxes[key].configure(state="normal")

        # A sequence only means something with a refinement to repeat.
        seq_ok = any(self.on(k) for k in SEQ_NEEDS)
        self.analysis_boxes["seq_para"].configure(
            state="normal" if seq_ok else "disabled")
        if not seq_ok:
            self.analysis["seq_para"].set(False)

        for key, _ in ANALYSES:
            self.nb.tab(self.tabs[key],
                        state="normal" if self.on(key) else "disabled")

        # Tk leaves a disabled tab selected; move to the leftmost live one.
        try:
            current = self.nb.select()
            if current and str(self.nb.tab(current, "state")) == "disabled":
                for key, _ in ANALYSES:
                    if self.on(key):
                        self.nb.select(self.tabs[key])
                        break
                else:
                    self.nb.select(self.tabs["future"])
        except tk.TclError:
            pass

        notes = []
        if pdf_on:
            notes.append("PDF can only be combined with Seq/Para — the others "
                         "have been switched off.")
        elif self.on("rietveld"):
            notes.append("Can be combined with Peak Fit/Index, Solve and Seq/Para.")
        elif self.on("peak_fitting") or self.on("solve"):
            notes.append("Can be combined with Riet and Seq.")
        if not seq_ok:
            notes.append("Seq/Para needs Riet or PDF — it repeats a refinement.")
        self.analysis_note.configure(text="  ".join(notes))

        self._sync_solve()
        self._sync_output_name()
        self.validate()

    def _sync_inferred_stages(self):
        """No structure on the Riet tab -> the job has to find one first, so
        Peak Fit and Solve tick themselves. A structure is entered -> they are
        not needed, and the two checkboxes DISAPPEAR.

        Only while Riet is ticked: on a PDF job the Riet tab is greyed and
        phase-less by definition, and this would tick boxes PDF has disabled.
        """
        if not hasattr(self, "analysis") or not self.on("rietveld"):
            return
        # A blank row defaults to source "cif", so test the PATH, not the
        # source.
        has_structure = any(
            (r.source_var.get() in ("cif", "str") and r.path_var.get().strip())
            or (r.source_var.get() == "pawley" and r.settings.get("space_group"))
            for r in self.phase_rows)

        for key in ("peak_fitting", "solve"):
            box = self.analysis_boxes[key]
            if has_structure:
                box.pack_forget()
                self.analysis[key].set(False)
            else:
                if not box.winfo_ismapped():
                    self._repack_analysis_boxes()
                # A hand click latches the box out of the auto-tick.
                if key not in self._auto_latched:
                    self.analysis[key].set(True)
        self._sync_check_styles()
        self._sync_analyses()

    def _sync_check_styles(self):
        """Grey tick = the form turned this on because it had to; blue tick =
        the user asked for it. Only the two inferred stages can be either."""
        for key in ("peak_fitting", "solve"):
            self.analysis_boxes[key].configure(
                style="TCheckbutton" if key in self._auto_latched
                else self.auto_check_style)

    def _repack_analysis_boxes(self):
        """Re-show the whole row in ANALYSES order; pack() alone would append
        the returning box to the right-hand end."""
        for key, _ in ANALYSES:
            self.analysis_boxes[key].pack_forget()
        for key, _ in ANALYSES:
            self.analysis_boxes[key].pack(side="left", padx=(0, 14))

    def _build_optional(self, parent):
        # ---- Corrections and range
        g1 = CollapsibleGroup(parent, "Corrections and range")
        g1.grid(row=0, column=0, sticky="ew")
        b = g1.body
        self.two_theta_label = ttk.Label(b, text="2θ range")
        self.two_theta_label.grid(row=0, column=0, sticky="w")
        self.tmin = ttk.Entry(b, width=8)
        self.tmin.grid(row=0, column=1, sticky="w", padx=(6, 2))
        ttk.Label(b, text="to").grid(row=0, column=2)
        self.tmax = ttk.Entry(b, width=8)
        self.tmax.grid(row=0, column=3, sticky="w", padx=(2, 0))
        ttk.Label(b, text="blank = whole file", foreground="grey").grid(
            row=0, column=4, sticky="w", padx=(8, 0))

        ttk.Label(b, text="2θ offset").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.offset = TriState(b, [("Sample height", "height"),
                                   ("Zero point", "zero"),
                                   ("Neither", "none")], width=20)
        self.offset.grid(row=1, column=1, columnspan=3, sticky="w", padx=(6, 0), pady=(6, 0))
        Tooltip(self.offset, "Height and zero-error shift peak positions almost "
                             "identically, so only one may be refined — refining "
                             "both is a correlation trap.")

        # ---- Peak shape & broadening
        g2 = CollapsibleGroup(parent, "Peak shape & broadening")
        g2.grid(row=1, column=0, sticky="ew")
        b = g2.body
        ttk.Label(b, text="Peak shape").grid(row=0, column=0, sticky="w")
        self.peak_shape = TriState(b, PEAK_SHAPES, width=30)
        self.peak_shape.grid(row=0, column=1, sticky="w", padx=(6, 0))
        self.peak_shape.bind("<<ComboboxSelected>>", lambda *_: self._sync_fp())

        self.fp_frame = ttk.Frame(b)
        self.fp_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        ttk.Label(self.fp_frame,
                  text="Instrument geometry — TOPAS source, pasted verbatim at xdd level:",
                  foreground="grey").pack(anchor="w")
        self.fp_text = tk.Text(self.fp_frame, height=9, width=64, font=("Consolas", 9),
                               wrap="none")
        self.fp_text.pack(fill="x")
        self.fp_seeded = ""

        self.size_strain = tk.BooleanVar(value=self.cfg["peak_shape"]["sample_size_strain"])
        cb = ttk.Checkbutton(
            b, text="Sample size/strain  (LVol_FWHM_CS_G_L + e0_from_Strain, refining)",
            variable=self.size_strain, command=self._sync_size_strain)
        cb.grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))
        Tooltip(cb, "Reporting wrappers around isotropic size/strain: LVol and e0 "
                    "are named in the .out instead of raw Lorentzian widths. "
                    "Ticking this fixes the TCHZ terms rather than refining them — "
                    "refining both is a strong correlation.")
        self.tchz_note = ttk.Label(b, text="", foreground="grey")
        self.tchz_note.grid(row=3, column=0, columnspan=3, sticky="w")

        ttk.Label(b, text="Axial model").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ax = ttk.Frame(b)
        ax.grid(row=4, column=1, columnspan=2, sticky="w", padx=(6, 0), pady=(8, 0))
        self.axial_len = ttk.Entry(ax, width=8)
        self.axial_len.insert(0, str(self.cfg["peak_shape"]["axial_length"]))
        self.axial_len.pack(side="left")
        self.refine_axial = tk.BooleanVar(value=self.cfg["peak_shape"]["refine_axial"])
        self.refine_axial_box = ttk.Checkbutton(ax, text="refine",
                                                variable=self.refine_axial)
        self.refine_axial_box.pack(side="left", padx=(6, 0))
        self.axial_note = ttk.Label(b, text="", foreground="grey")
        self.axial_note.grid(row=5, column=0, columnspan=3, sticky="w")
        self.tof_note = ttk.Label(b, text="", foreground="#7a5c1e", wraplength=460,
                                  justify="left")
        self.tof_note.grid(row=6, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # ---- Refinement control
        g3 = CollapsibleGroup(parent, "Background & staging")
        g3.grid(row=2, column=0, sticky="ew")
        b = g3.body
        ttk.Label(b, text="Background order").grid(row=0, column=0, sticky="w")
        self.bkg = ttk.Entry(b, width=8)
        self.bkg.insert(0, str(self.cfg["refinement"]["background_order"]))
        self.bkg.grid(row=0, column=1, sticky="w", padx=(6, 0))
        ttk.Label(b, text="Chebyshev", foreground="grey").grid(row=0, column=2, sticky="w",
                                                               padx=(6, 0))

        ttk.Label(b, text="First cycle refines").grid(row=1, column=0, sticky="nw", pady=(6, 0))
        fc = ttk.Frame(b)
        fc.grid(row=1, column=1, columnspan=2, sticky="w", padx=(6, 0), pady=(6, 0))
        self.first_cycle = {}
        for key, label in (("scale_background", "scale + background"),
                           ("offset", "offset correction"),
                           ("lattice", "lattice"),
                           ("peak_shape", "peak shape"),
                           ("atoms_adps", "atoms + ADPs")):
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(fc, text=label, variable=var).pack(anchor="w")
            self.first_cycle[key] = var

        self._sync_fp()
        self._sync_size_strain()

    def _build_job(self):
        """Mode and output. Parented to root so expanding an optional group
        cannot push OK off-screen."""
        f = ttk.LabelFrame(self._host, text=" 4 · What to do with the .inp file ",
                           style="Section.TLabelframe", padding=(10, 6))
        f.grid(row=3, column=0, sticky="ew", padx=12, pady=(2, 4))
        f.columnconfigure(0, minsize=self._label_col)   # see _build_measurement
        f.columnconfigure(1, weight=3, minsize=FIELD_COL_MIN)
        f.columnconfigure(3, weight=1)
        ttk.Frame(f).grid(row=99, column=3, sticky="ew")

        ttk.Label(f, text="Mode").grid(row=0, column=0, sticky="w")
        modes = ttk.Frame(f)
        modes.grid(row=0, column=1, columnspan=3, sticky="w", padx=6)
        self.mode = tk.StringVar(value=self.cfg["general"]["mode"])
        for value, label in (("create_and_run", "Create the .inp and run it"),
                             ("create_only", "Create the .inp only"),
                             ("continue", "Continue an existing refinement")):
            ttk.Radiobutton(modes, text=label, variable=self.mode, value=value,
                            command=self._on_mode).pack(side="left", padx=(0, 12))

        # ONE path box, not two: the output path already carries a directory.
        # Whatever folder it points at is where the job file and everything
        # else goes, and it is remembered between sessions.
        req(f, "Output .inp").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.out_var = tk.StringVar()
        self.out_var.trace_add("write", lambda *_: self.validate())
        ttk.Entry(f, textvariable=self.out_var).grid(row=1, column=1, sticky="ew",
                                                     padx=6, pady=(6, 0))
        ttk.Button(f, text="Browse…", command=self._browse_out).grid(row=1, column=2,
                                                                     pady=(6, 0))
        ttk.Label(f, text="Most other files will be written to this same folder",
                  foreground="grey").grid(row=2, column=1, columnspan=3,
                                          sticky="w", padx=6)

    def _build_buttons(self):
        # Outside the scroller on purpose: OK must never scroll off screen.
        bar = ttk.Frame(self, padding=(12, 6))
        bar.grid(row=1, column=0, sticky="ew")
        self._btn_bar = bar
        legend = ttk.Frame(bar)
        legend.pack(side="left", padx=(0, 14))
        ttk.Label(legend, text="*", style="Req.TLabel").pack(side="left")
        ttk.Label(legend, text=" required", foreground="grey").pack(side="left")
        self.status = ttk.Label(bar, text="", foreground="#a05000")
        self.status.pack(side="left")
        self.ok_btn = ttk.Button(bar, text="OK", command=self.on_ok, default="active")
        self.ok_btn.pack(side="right")
        ttk.Button(bar, text="Cancel", command=self.on_cancel).pack(side="right", padx=(0, 6))
        ttk.Button(bar, text="Save as defaults", command=self.on_save_defaults).pack(
            side="right", padx=(0, 16))
        ttk.Button(bar, text="Load job\u2026", command=self.on_load_job).pack(
            side="right", padx=(0, 6))

    # -- reactions ---------------------------------------------------------
    def last_dir(self) -> str:
        """Where a file dialog should open: this job's folder if one is chosen,
        else the folder used last session, else cwd."""
        data = self.data_var.get().strip()
        if data and Path(data).parent.is_dir():
            return str(Path(data).parent)
        if self._last_dir and Path(self._last_dir).is_dir():
            return self._last_dir
        return os.getcwd()

    def _remember_dir(self, path: str):
        self._last_dir = str(Path(path).parent)

    def _browse_data(self):
        mode = self.data_mode.get()
        if mode == "dir":
            path = filedialog.askdirectory(title="Choose the folder of data files",
                                           initialdir=self.last_dir())
        elif mode == "list":
            path = filedialog.askopenfilename(
                title="Choose the list file",
                initialdir=self.last_dir(),
                filetypes=[("Table", "*.csv *.tsv *.txt"), ("All files", "*.*")])
        else:
            path = filedialog.askopenfilename(title="Choose the powder data file",
                                              initialdir=self.last_dir(),
                                              filetypes=DATA_FILETYPES)
        if path:
            self._remember_dir(path)
            self.data_var.set(path)

    def _on_data_mode(self):
        """Directory and list mode both mean many datasets, so they turn Seq/Para
        on -- and Riet with it when nothing else would give the sequence
        something to repeat."""
        mode = self.data_mode.get()
        self.data_label.winfo_children()[0].configure(
            text={"file": "Data file", "dir": "Data folder",
                  "list": "List file"}[mode])
        self.data_var.set("")
        if mode in ("dir", "list"):
            if not any(self.on(k) for k in SEQ_NEEDS):
                self.analysis["rietveld"].set(True)
            self.analysis["seq_para"].set(True)
        else:
            self.analysis["seq_para"].set(False)
        self._sync_analyses()
        self._on_data_changed()

    def data_files(self) -> list[Path]:
        """Every dataset the job covers. Natural-sorted so _2 precedes _10."""
        raw = self.data_var.get().strip()
        if not raw:
            return []
        p = Path(raw)
        if self.data_mode.get() == "dir":
            if not p.is_dir():
                return []
            return sorted((f for f in p.iterdir()
                           if f.suffix.lower() in DATA_SUFFIXES),
                          key=lambda f: natural_key(f.name))
        return [p] if p.is_file() else []

    def _browse_out(self):
        if self.mode.get() == "continue":
            path = filedialog.askopenfilename(title="Choose the .inp to continue",
                                              initialdir=self.last_dir(),
                                              filetypes=[("TOPAS input", "*.inp")])
        else:
            path = filedialog.asksaveasfilename(title="Output .inp",
                                                initialdir=self.last_dir(),
                                                defaultextension=".inp",
                                                filetypes=[("TOPAS input", "*.inp")])
        if path:
            self._remember_dir(path)
            self._out_dir = str(Path(path).parent)
            self._out_dir_pinned = True
            self.out_var.set(path)

    def _on_data_changed(self):
        if self.data_mode.get() == "dir":
            n = len(self.data_files())
            self.data_note.configure(
                text=f"{n} data file{'' if n == 1 else 's'} found"
                if self.data_var.get().strip() else "")
        else:
            self.data_note.configure(text="")
        # Empty in every mode but "dir", where it counts the files. Left
        # gridded it holds a blank line open between Data file and Instrument.
        note_on = bool(self.data_note.cget("text"))
        if note_on != getattr(self, "_data_note_on", True):
            self._data_note_on = note_on
            (self.data_note.grid if note_on else self.data_note.grid_remove)()
        self._sync_output_name()
        self.validate()

    def _sync_output_name(self):
        """Stem from the data file, or from the folder's name in the multi-file
        modes. Suffix from the last stage that writes a fit, not the visible
        tab -- several stages can be active at once."""
        # _load_job restores the output path the FILE names; regenerating over
        # it would bump the suffix and point the job at a different file.
        if getattr(self, "_loading", False):
            return
        if not hasattr(self, "out_var") or self.mode.get() == "continue":
            return
        raw = self.data_var.get().strip()
        if not raw:
            return
        p = Path(raw)
        if self.data_mode.get() == "dir":
            # Everything the job writes goes one level UP from the data
            # folder, beside the dataset rather than inside it.
            # p.parent == p only at a drive root, where there is no "up".
            stem = p.name or "series"
            folder = p.parent if p.parent != p else p
        else:
            stem, folder = p.stem or "refinement", p.parent

        # A folder the user has pointed output at THIS session wins over the
        # data's own folder, so choosing it once carries to the next dataset
        # -- but only this session's own choice, never merely what a past
        # session's config remembers, or a fresh dataset in an unrelated
        # folder would silently inherit yesterday's output location.
        if self._out_dir_pinned and self._out_dir and Path(self._out_dir).is_dir():
            folder = Path(self._out_dir)
        self.out_var.set(str(next_free_output(folder, stem, self.active_stages())))

    def radiation_kind(self) -> str:
        """'cw' or 'tof'. An instrument entry with no radiation_kind is CW;
        defaulting the other way would silently make every such entry ToF."""
        instr = self.current_instrument()
        return (instr or {}).get("radiation_kind", "cw")

    def _sync_radiation(self):
        """ToF is not a CW 2-theta measurement, so six controls change with it.
        The gate is radiation_kind, never the instrument's name."""
        tof = self.radiation_kind() == "tof"

        # Wavelength box becomes the instrument name: a white beam has no one
        # wavelength, but which spectrometer it was matters.
        self.wl_text.configure(text="Instrument name" if tof else "Wavelength")
        if tof:
            self.wl_note.configure(text="e.g. POLARIS, HRPD")
            self.wl_entry.configure(state="normal")
            self._show_wl_entry(True)
            self.wl_star.pack(side="left")

        # _sync_slits owns both rules: ToF has no divergence slit, and nor has
        # anything outside Bragg-Brentano.
        self._sync_slits()

        # TCHZ and fundamental parameters are CW profiles; ToF wants
        # back-to-back exponentials, so offer neither rather than a wrong one.
        shapes = [(l, v) for l, v in PEAK_SHAPES if v == "size_strain"] if tof \
            else PEAK_SHAPES
        if getattr(self, "_shape_tof", None) != tof:
            self._shape_tof = tof
            self.peak_shape.set_options(shapes)
            self.pf_peak_shape.set_options(
                shapes + [("One pseudo-Voigt per peak", "pv_per_peak")])

        # Simple_Axial_Model is a Bragg-Brentano correction; sample height and
        # zero point are 2-theta shifts with no ToF meaning.
        for widget in (self.axial_len, self.refine_axial_box, self.offset):
            widget.configure(state="disabled" if tof else "normal")
        self.tof_note.configure(
            text=("Time-of-flight: slits, axial model and 2θ offset do not apply, "
                  "and the peak shape is left to TOPilot." if tof else ""))
        self.two_theta_label.configure(text="Range (TOF / d)" if tof else "2θ range")

        # The seeded 70 is degrees, so it must not carry onto a ToF axis -- but
        # clear it only while the box still holds the seed itself. Compare
        # against the seed rather than tracking who typed it: prefill restores
        # two_theta_max, which would otherwise count as "touched" for ever.
        seed = getattr(self, "_tmax_seed", None)
        if seed is not None:
            if tof:
                if self.tmax.get().strip() == str(seed):
                    self.tmax.delete(0, "end")
            elif (not self.tmax.get().strip()
                    and not getattr(self, "_tmax_touched", False)):
                self.tmax.insert(0, str(seed))

    def _show_wl_entry(self, show: bool):
        """The note sits to the RIGHT of the entry, so an instrument that
        supplies its own emission strands the text past an empty greyed box;
        drop the box in that one case."""
        self.wl_entry.pack_forget()
        self.wl_note.pack_forget()
        if show:
            self.wl_entry.pack(side="left")
            self.wl_note.pack(side="left", padx=(8, 0))
        else:
            self.wl_note.pack(side="left")

    def _slits_apply(self) -> bool:
        """A variable divergence slit is a Bragg-Brentano fitting; the BB_
        entries are the instruments that have one. A capillary, synchrotron or
        neutron measurement has nothing for the option to mean, and ToF has no
        divergence slit at all. Only a named BB instrument shows the control:
        with nothing picked, or with "None specified", the form cannot tell
        whether there is a slit, and the user says so in section 2 instead."""
        if self.radiation_kind() == "tof":
            return False
        choice = self.instr_box.get()
        if choice in (PICK_INSTRUMENT, NO_INSTRUMENT):
            return False
        return choice.startswith("BB")

    def _sync_slits(self):
        """Hiding clears the value as well: a slit mode left over from an
        earlier instrument would otherwise be emitted by a job whose form no
        longer shows it."""
        if self._slits_apply():
            self.slits_label.grid()
            self.slits.grid()
        else:
            self.slits_label.grid_remove()
            self.slits.grid_remove()
            self.slits.set_value(None)

    def _on_instrument(self):
        instr = self.current_instrument()
        self._sync_radiation()
        if self.radiation_kind() == "tof":
            self.validate()
            return
        if self.instr_box.get() == PICK_INSTRUMENT:
            self.wl_entry.configure(state="disabled")
            self._show_wl_entry(True)     # empty note: keep the placeholder box
            self.wl_note.configure(text="")
            self.wl_star.pack_forget()
            self.validate()
            return
        if instr is None:
            # No instrument chosen: leave the box usable but require nothing.
            self.wl_entry.configure(state="normal")
            self._show_wl_entry(True)
            self.wl_star.pack_forget()          # optional without an instrument
            self.wl_note.configure(
                text="optional — say what the instrument was in section 2")
            self.validate()
            return
        needs = bool(instr.get("needs_wavelength"))
        self.wl_entry.configure(state="normal" if needs else "disabled")
        self._show_wl_entry(needs)
        if needs:
            self.wl_star.pack(side="left")
        else:
            self.wl_star.pack_forget()
        self.wl_note.configure(
            text="" if needs else f"{instr.get('emission', '')}  (from instrument)")
        # Seed the FP box from this instrument, unless the user has edited it.
        current = self.fp_text.get("1.0", "end").strip()
        if current in ("", self.fp_seeded.strip()):
            block = (instr.get("fp_block") or "").strip()
            self.fp_text.delete("1.0", "end")
            self.fp_text.insert("1.0", block)
            self.fp_seeded = block
        self.validate()

    def _on_mode(self):
        """Continue describes an .inp that already exists, so every
        creation-time control is greyed -- including all the analysis tabs."""
        cont = self.mode.get() == "continue"
        for w in (self.instr_box,):
            w.configure(state="disabled" if cont else "readonly")
        for key, _ in ANALYSES:
            self.analysis_boxes[key].configure(state="disabled" if cont else "normal")
            self.nb.tab(self.tabs[key],
                        state="disabled" if cont or not self.on(key) else "normal")
        if cont:
            self.nb.select(self.tabs["future"])
        else:
            self._sync_analyses()
        self.iters_note.configure(text="")
        self._sync_iters()
        self.validate()

    def _sync_fp(self):
        is_fp = self.peak_shape.value() == "fp"
        for child in self.fp_frame.winfo_children():
            child.configure(state="normal" if is_fp else "disabled")
        self.fp_text.configure(state="normal" if is_fp else "disabled")
        self._sync_size_strain()

    def _sync_size_strain(self):
        on = self.size_strain.get()
        tchz = self.peak_shape.value() != "fp"
        self.tchz_note.configure(
            text=("      TCHZ terms will be FIXED (!) as the instrument resolution "
                  "function" if (on and tchz) else ""))
        is_fp = self.peak_shape.value() == "fp"
        self.axial_note.configure(
            text="      disabled: fundamental parameters handles axial divergence itself"
            if is_fp else "")
        state = "disabled" if is_fp else "normal"
        self.axial_len.configure(state=state)

    def current_instrument(self) -> dict | None:
        name = self.instr_box.get()
        for i in self.instruments:
            if i["name"] == name:
                return i
        return None

    def add_phase_row(self, data: dict | None = None) -> PhaseRow:
        row = PhaseRow(self.phase_host, self)
        row.pack(fill="x", pady=2)
        self.phase_rows.append(row)
        if data:
            row.from_dict(data)
        self._sync_inferred_stages()
        self.validate()
        return row

    def remove_row(self, row: PhaseRow):
        if row in self.phase_rows:
            self.phase_rows.remove(row)
            row.destroy()
        self._sync_inferred_stages()
        self.validate()

    def _solve_problems(self) -> list[str]:
        """The Solve tab's own requirements. Cell and space group are required
        only when nothing upstream supplies them."""
        out = []
        if not self.on("peak_fitting") and not self.solve_cell.complete():
            out.append("Solve needs a cell and space group")
        cf = self.solve_method.get() == "charge_flipping"
        molecular = (not cf) and self.solve_kind.get() == "molecular"
        if not molecular and not self.contents.get().strip():
            out.append("Solve needs the empirical formula, e.g. Pb S O4")
        if molecular:
            if self.zmat_source.get() == "file":
                path = self.zmat_path.get().strip()
                if not path:
                    out.append("choose the CIF holding the molecular fragment")
                elif not Path(path).is_file():
                    out.append("that fragment CIF does not exist")
            elif not self.zmat_text.get("1.0", "end").strip():
                out.append("paste a Z-matrix or rigid body")
        return out

    # -- validation --------------------------------------------------------
    def validate(self, *_):
        """Paths exist, numerics parse, required fields present. No physics."""
        # Tab builders call this while the form is still being assembled,
        # before self.mode exists. _build() validates once at the end anyway.
        if not hasattr(self, "mode") or not hasattr(self, "ok_btn"):
            return False
        # _load_job sets one field at a time and each one traces back here,
        # so loading N phases ran this whole method -- including the O(N) scan
        # over every phase row below -- on the order of 10N times, for O(N^2)
        # total: 50 phases took ~5.6s here alone. None of those intermediate
        # results are ever painted -- Tk does not redraw until this call
        # returns to the event loop, and _load_job runs one guaranteed final
        # validate() once every field is in, after _loading clears -- so
        # skipping them costs nothing and turns the whole load back into O(N).
        if getattr(self, "_loading", False):
            return False
        problems = []
        tab_problems: dict[str, list[str]] = {}   # continue mode: every tab clears
        if self.mode.get() == "continue":
            out = self.out_var.get().strip()
            if not out:
                problems.append("choose the .inp to continue")
            elif not Path(out).is_file():
                problems.append("that .inp does not exist")
        else:
            if not self.active_stages():
                problems.append("choose at least one analysis type")

            data = self.data_var.get().strip()
            mode = self.data_mode.get()
            if not data:
                problems.append({"dir": "choose a data folder",
                                 "list": "choose a list file"}.get(
                                     mode, "choose a data file"))
            elif mode == "dir":
                if not Path(data).is_dir():
                    problems.append("that folder does not exist")
                elif not self.data_files():
                    problems.append("no readable data files in that folder")
            elif not Path(data).is_file():
                problems.append("data file does not exist")

            out = self.out_var.get().strip()
            if not out:
                problems.append("output path")
            elif not Path(out).parent.is_dir():
                problems.append("that output folder does not exist")

            instr = self.current_instrument()
            tof = self.radiation_kind() == "tof"
            if self.instr_box.get() == PICK_INSTRUMENT:
                problems.append("choose an instrument")
            elif instr is None and self.instr_box.get() != NO_INSTRUMENT:
                problems.append("choose an instrument")
            elif tof and not self.wl_var.get().strip():
                problems.append("name the ToF instrument, e.g. POLARIS")
            elif instr and instr.get("needs_wavelength") and not self.wl_var.get().strip():
                problems.append("this instrument needs a wavelength")

            tab_problems = self._tab_problems(tof)
            for lst in tab_problems.values():
                problems.extend(lst)

        self._sync_tab_flags(tab_problems)
        ok = not problems
        if hasattr(self, "ok_btn"):
            self.ok_btn.configure(state="normal" if ok else "disabled")
            self.status.configure(text="" if ok else "  ·  ".join(problems[:3]))
        return ok

    def _tab_problems(self, tof: bool) -> dict[str, list[str]]:
        """Requirements specific to one analysis tab, keyed by stage. Feeds
        both the flat status-line list above and the tab-strip flag icon --
        only a ticked tab appears here, so an unticked one always clears."""
        out: dict[str, list[str]] = {}
        if self.on("peak_fitting"):
            pf = []
            if self.pf_method.current() == 2 and not self.peakfit_peaks():
                pf.append("paste at least one 2theta value, or use the "
                         "default peak search")
            if tof:
                pf.append("indexing ToF data is not supported yet")
            out["peak_fitting"] = pf
        if self.on("solve"):
            out["solve"] = self._solve_problems()
        if self.on("rietveld"):
            rows_out = []
            supplies_structure = self.on("solve") or self.on("peak_fitting")
            if not self.phase_rows and not supplies_structure:
                rows_out.append("add at least one phase")
            for row in self.phase_rows:
                # An untouched row is filler, not a phase awaiting a file --
                # it must not force a structure choice the pipeline already
                # makes elsewhere. A row someone has started (a name typed,
                # a Pawley source picked) still has to be finished.
                if not (supplies_structure and row.is_blank()):
                    rows_out.extend(row.problems())
                row.refresh_summary()   # keeps each row's button label in step
            out["rietveld"] = rows_out
        return out

    # -- config ------------------------------------------------------------
    def _apply_config(self):
        """Apply hand-written assertions from the config files to the controls.
        Without this the keys load and do nothing. Runs before _prefill so
        the last job still wins."""
        cfg = self.cfg
        self._iters_touched = False

        slits = cfg.get("measurement", {}).get("variable_slits")
        if slits in ("fixed", "variable"):
            self.slits.set_value(slits)

        self._tmax_seed = cfg.get("corrections", {}).get("two_theta_max")
        self._tmax_touched = False
        if self._tmax_seed is not None and self.radiation_kind() != "tof":
            self.tmax.insert(0, str(self._tmax_seed))
        self.tmax.bind("<Key>", lambda _e: setattr(self, "_tmax_touched", True))
        self.tmin.bind("<Key>", lambda _e: setattr(self, "_tmax_touched", True))

        offset = cfg.get("corrections", {}).get("offset_correction")
        if offset == "from_geometry":
            instr = self.current_instrument()
            offset = instr.get("offset_correction") if instr else None
        if offset in ("height", "zero", "none"):
            self.offset.set_value(offset)

        model = cfg.get("peak_shape", {}).get("model")
        if model in ("tchz", "fp"):
            self.peak_shape.set_value(model)
            self._sync_fp()

        ref = cfg.get("refinement", {})
        if isinstance(ref.get("do_errors"), bool):
            self.do_errors.set_value(ref["do_errors"])
        if isinstance(ref.get("continue_after_convergence"), bool):
            self.cac.set_value(ref["continue_after_convergence"])
        for key in ref.get("first_cycle") or []:
            if key in self.first_cycle:
                self.first_cycle[key].set(True)

        self._sync_iters()
        self.iters.bind("<KeyRelease>", self._on_iters_typed, add="+")

    def _on_iters_typed(self, _evt=None):
        self._iters_touched = True

    def _sync_iters(self):
        """iters follows the mode until the user types in the box: 0 for
        create-only (iters 0 skips refinement entirely), the run value otherwise.
        Clearing the box leaves it unspecified, like any other optional field."""
        if getattr(self, "_iters_touched", False):
            return
        # One count for every mode: a create-only .inp exists so it can be run.
        ref = self.cfg.get("refinement", {})
        value = ref.get("iters_run", 1000)
        self.iters.delete(0, "end")
        self.iters.insert(0, str(value))

    # -- prefill -----------------------------------------------------------
    def _prefill(self):
        """Restore the previous job via last_job_path. Only keys PRESENT in the
        file are restored, so inferred values never become assertions."""
        local = HERE / "wizard_defaults.local.json"
        prev = None
        if local.is_file():
            try:
                pointer = json.loads(local.read_text(encoding="utf-8")).get("last_job_path")
                if pointer and Path(pointer).is_file():
                    prev = json.loads(Path(pointer).read_text(encoding="utf-8"))
            except Exception as exc:
                self.warnings.append(f"prefill: {exc}")
        if not prev:
            self.add_phase_row()
            self._on_instrument()
            self._on_mode()
            return
        if prev.get("schema") != SCHEMA:
            self.warnings.append(
                f"previous job file is schema {prev.get('schema')}, this wizard "
                f"writes {SCHEMA} -- not prefilled")
            self.add_phase_row()
            self._on_instrument()
            self._on_mode()
            return

        # Settings are restored; identities (data file, output, phases) are not
        # -- carrying those forward mislabels the next job. on_load_job does.
        self._apply_settings(prev)
        # Phases are identities: always start with one empty row.
        self.add_phase_row()

        self._on_instrument()
        if prev.get("fp_block"):
            self.fp_text.delete("1.0", "end")
            self.fp_text.insert("1.0", prev["fp_block"])
        self._on_mode()
        self._sync_fp()

    def _apply_settings(self, prev: dict):
        """The half of a job file that describes HOW to refine rather than WHAT
        -- shared by the automatic prefill and the Load job button."""
        g = prev.get

        if g("mode"):
            self.mode.set(g("mode"))
        if g("rules"):
            self.rules.set(g("rules"))
        # Instrument is NOT restored by prefill, alone among the settings:
        # inheriting the wrong one puts every calculated peak in the wrong
        # place. on_load_job restores it explicitly.
        if g("wavelength") is not None:
            self.wl_var.set(str(g("wavelength")))
        if g("variable_slits") is not None:
            self.slits.set_value(g("variable_slits"))
        if g("offset_correction") is not None:
            self.offset.set_value(g("offset_correction"))
        if g("peak_shape") is not None:
            self.peak_shape.set_value(g("peak_shape"))
        if g("sample_size_strain") is not None:
            self.size_strain.set(bool(g("sample_size_strain")))
        if g("extra"):
            pass                       # extra is job-specific; not carried over
        if g("two_theta_range"):
            lo, hi = g("two_theta_range")
            self.tmin.delete(0, "end"); self.tmin.insert(0, str(lo))
            self.tmax.delete(0, "end"); self.tmax.insert(0, str(hi))
            self._tmax_touched = True
        else:
            for key, widget in (("two_theta_min", self.tmin),
                                ("two_theta_max", self.tmax)):
                if g(key) is not None:
                    widget.delete(0, "end")
                    widget.insert(0, str(g(key)))
                    self._tmax_touched = True
        for key, widget in (("background_order", self.bkg), ("iters", self.iters),
                            ("axial_length", self.axial_len)):
            if g(key) is not None:
                widget.delete(0, "end")
                widget.insert(0, str(g(key)))
        if g("refine_axial") is not None:
            self.refine_axial.set(bool(g("refine_axial")))
        if g("do_errors") is not None:
            self.do_errors.set_value(g("do_errors"))
        if g("continue_after_convergence") is not None:
            self.cac.set_value(g("continue_after_convergence"))
        for key in g("first_cycle") or []:
            if key in self.first_cycle:
                self.first_cycle[key].set(True)

    # -- loading a job file by hand ----------------------------------------
    def on_load_job(self):
        """Repopulate the whole form from a job file the user picks. Unlike the
        automatic prefill this restores IDENTITIES too -- data, output, phases,
        instrument -- because naming the file is itself the instruction."""
        path = filedialog.askopenfilename(
            title="Load a job file", initialdir=self.last_dir(),
            filetypes=[("TOPilot job", "*_job.json"), ("JSON", "*.json"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            job = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("TOPAS job wizard", f"Could not read that file:\n{exc}")
            return
        if job.get("schema") != SCHEMA:
            messagebox.showerror(
                "TOPAS job wizard",
                f"That job file is schema {job.get('schema')}; this wizard "
                f"reads {SCHEMA}. Not loaded.")
            return
        self._remember_dir(path)
        notes = self._load_job(job)
        if notes:
            messagebox.showwarning("TOPAS job wizard",
                                   "Loaded, with:\n\n  " + "\n  ".join(notes))

    def _load_job(self, job: dict) -> list[str]:
        """Apply a whole job file. Returns notes about anything that could not
        be restored faithfully. Order matters throughout -- see the comments."""
        g, notes = job.get, []
        self._loading = True

        # 1. Stages first: they decide which tabs are live for everything below.
        #    A loaded job states its stages outright, so both inferred boxes are
        #    LATCHED either way -- otherwise the inferred-stage rule would tick
        #    Peak Fit and Solve back on over a job that deliberately omits them.
        stages = set(g("workflows") or [])
        for key in STAGES:
            self.analysis[key].set(key in stages)
        self._auto_latched.update(("peak_fitting", "solve"))
        seq = g("sequential") or {}
        self.analysis["seq_para"].set(bool(seq))
        if seq:
            if seq.get("mode"):
                self.seq_mode.set(seq["mode"])
            self.seq_reel.set(bool(seq.get("reel_output")))
        self._sync_analyses()
        self._sync_check_styles()

        # 2. Data. Set the mode variable directly: _on_data_mode() clears the
        #    path and forces Seq/Para on, both of which would undo step 1.
        if g("data_mode"):
            mode = g("data_mode")
            self.data_mode.set(mode)
            self.data_label.winfo_children()[0].configure(
                text={"file": "Data file", "dir": "Data folder",
                      "list": "List file"}.get(mode, "Data file"))
        if g("data") is not None:
            self.data_var.set(g("data"))        # fires _on_data_changed
            if not Path(g("data")).exists():
                notes.append(f"the data path no longer exists: {g('data')}")

        # 3. The file list is DERIVED from the folder, never stored in the
        #    form, so say so when the folder no longer holds what the job was
        #    built from.
        recorded = g("data_files") or []
        if recorded:
            now = len(self.data_files())
            if now != len(recorded):
                notes.append(f"the folder held {len(recorded)} data files when "
                             f"this job was saved and holds {now} now")

        # 4. Instrument before wavelength: _on_instrument() rewrites the
        #    wavelength box and reseeds the FP block from the instrument.
        if g("instrument"):
            names = [i["name"] for i in self.instruments]
            if g("instrument") in names:
                self.instr_box.set(g("instrument"))
            else:
                notes.append(f"instrument {g('instrument')!r} is not in "
                             f"instrument_descriptions.toml")
        elif g("data_mode"):
            self.instr_box.set(NO_INSTRUMENT)
        self._on_instrument()
        if g("radiation_kind") == "tof" and g("instrument_name"):
            self.wl_var.set(g("instrument_name"))

        # 5. Everything that describes HOW to refine.
        self._apply_settings(job)
        if g("fp_block"):
            self.fp_text.delete("1.0", "end")
            self.fp_text.insert("1.0", g("fp_block"))
        self.extra.delete("1.0", "end")
        if g("extra"):
            self.extra.insert("1.0", g("extra"))

        # 6. Per-tab fields.
        self._load_peak_fitting(job)
        self._load_solve(job)

        # 7. Phases: drop every existing row, then rebuild from the file.
        for row in list(self.phase_rows):
            self.remove_row(row)
        for phase in g("phases") or []:
            self.add_phase_row(phase)
        if not self.phase_rows:
            self.add_phase_row()

        self._on_mode()
        self._sync_fp()
        self._sync_solve()
        self._sync_radiation()

        # 8. Output LAST: several syncs above reach _sync_output_name, which is
        #    why the whole load is guarded by self._loading.
        self._loading = False
        if g("out"):
            self.out_var.set(g("out"))
            self._out_dir = str(Path(g("out")).parent)
            self._out_dir_pinned = True   # this file was chosen by hand

        self.validate()
        return notes

    def _load_peak_fitting(self, job: dict):
        g = job.get
        method = {"default": 1, "list": 2}.get(g("peak_search_method"))
        if method is not None:
            self.pf_method.current(method)
        if g("peak_fit") is not None:
            self.pf_fit.set(bool(g("peak_fit")))
        if g("peak_fit_shape") is not None:
            self.pf_peak_shape.set_value(g("peak_fit_shape"))
        if g("peak_fit_refine_axial") is not None:
            self.pf_refine_axial.set(bool(g("peak_fit_refine_axial")))
        if g("index") is not None:
            self.pf_index.set(bool(g("index")))
        if g("pawley") is not None:
            self.pf_pawley.set(bool(g("pawley")))
        for key, widget in (("index_min_intensity_pct", self.pf_min_pct),
                            ("pawley_top_n", self.pf_top_n)):
            if g(key) is not None:
                widget.delete(0, "end")
                widget.insert(0, str(g(key)))

    def _load_solve(self, job: dict):
        solve = job.get("solve") or {}
        if not solve:
            return
        if solve.get("method"):
            self.solve_method.set(solve["method"])
        # cell_from means the cell comes from the stage before, so there is
        # nothing to put in the boxes -- leaving them blank is the restore.
        if solve.get("space_group"):
            self.solve_cell.set_value(solve)
        if solve.get("structure"):
            self.solve_kind.set(solve["structure"])
        if solve.get("fragment_source"):
            self.zmat_source.set(solve["fragment_source"])
        if solve.get("fragment_file"):
            self.zmat_path.set(solve["fragment_file"])
        if solve.get("fragment_text"):
            self.zmat_text.delete("1.0", "end")
            self.zmat_text.insert("1.0", solve["fragment_text"])
        if solve.get("empirical_formula") is not None:
            self.contents.delete(0, "end")
            self.contents.insert(0, solve["empirical_formula"])
        if solve.get("z") is not None:
            self.solve_z.delete(0, "end")
            self.solve_z.insert(0, str(solve["z"]))

    # -- output ------------------------------------------------------------
    def collect(self) -> dict:
        """Build the job dict. Unset optional fields are OMITTED, never null."""
        job = {
            "schema": SCHEMA,
            # A LIST, in pipeline order: several stages can run in one job.
            "workflows": self.active_stages(),
            "mode": self.mode.get(),
            "created": datetime.now().isoformat(timespec="seconds"),
            "out": as_posix(self.out_var.get().strip()),
        }
        extra = self.extra.get("1.0", "end").strip()

        if self.mode.get() == "continue":
            # A continue job describes a file that already exists; the
            # creation-time fields must not be re-derived from the form.
            if extra:
                job["extra"] = extra
            return job

        job["data"] = as_posix(self.data_var.get().strip())
        job["data_mode"] = self.data_mode.get()
        if self.data_mode.get() == "dir":
            job["data_files"] = [as_posix(str(f)) for f in self.data_files()]
        # rules names a subset of the RIETVELD conventions, so it is meaningless
        # on any other tab and must not leak into its job file.
        if self.on("rietveld"):
            job["rules"] = self.rules.get()
        instr = self.current_instrument()
        tof = self.radiation_kind() == "tof"
        if instr:
            job["instrument"] = instr["name"]
            job["radiation_kind"] = self.radiation_kind()
        if tof:
            # White beam: the box holds the spectrometer's name, not a number.
            name = self.wl_var.get().strip()
            if name:
                job["instrument_name"] = name
        else:
            wl = num_or_none(self.wl_var.get())
            if wl is not None and (instr is None or instr.get("needs_wavelength")):
                job["wavelength"] = wl

        def put(key, value):
            if value is not None:
                job[key] = value

        put("variable_slits",
            self.slits.value() if self._slits_apply() else None)
        put("offset_correction", self.offset.value())

        # One end alone is a real answer, so it gets its own key rather than a
        # two-element list with a null in it: an unset field is omitted, never
        # written null.
        lo, hi = num_or_none(self.tmin.get()), num_or_none(self.tmax.get())
        if lo is not None and hi is not None:
            job["two_theta_range"] = [lo, hi]
        elif hi is not None:
            job["two_theta_max"] = hi
        elif lo is not None:
            job["two_theta_min"] = lo

        shape = self.peak_shape.value()
        put("peak_shape", shape)
        if shape == "fp":
            block = self.fp_text.get("1.0", "end").strip()
            if block:
                job["fp_block"] = block
                job["fp_source"] = ("instrument"
                                    if block == self.fp_seeded.strip() else "user_edited")
        else:
            put("axial_length", num_or_none(self.axial_len.get()))
            job["refine_axial"] = self.refine_axial.get()

        job["sample_size_strain"] = self.size_strain.get()
        put("background_order", num_or_none(self.bkg.get(), int))
        put("iters", num_or_none(self.iters.get(), int))
        put("do_errors", self.do_errors.value())
        put("continue_after_convergence", self.cac.value())

        chosen = [k for k, v in self.first_cycle.items() if v.get()]
        if chosen:
            job["first_cycle"] = chosen

        # ---- each ticked tab adds only its own keys ------------------------
        if self.on("peak_fitting"):
            # index 0 is "Choose…" -- left there, the key is omitted and the
            # skill decides, like any other unset field.
            if self.pf_method.current() == 2:
                job["peak_search_method"] = "list"
                job["peaks_2th"] = self.peakfit_peaks()
            elif self.pf_method.current() == 1:
                job["peak_search_method"] = "default"
            job["peak_fit"] = self.pf_fit.get()
            if self.pf_fit.get():
                job["peak_fit_shape"] = self.pf_peak_shape.value()
                job["peak_fit_refine_axial"] = self.pf_refine_axial.get()
            job["index"] = self.pf_index.get()
            if self.pf_index.get():
                put("index_min_intensity_pct", num_or_none(self.pf_min_pct.get()))
            job["pawley"] = self.pf_pawley.get()
            if self.pf_pawley.get():
                put("pawley_top_n", num_or_none(self.pf_top_n.get(), int))

        if self.on("solve"):
            cf = self.solve_method.get() == "charge_flipping"
            solve = {"method": self.solve_method.get()}
            # A cell typed here wins over the indexed one; left blank with
            # indexing running, the cell comes from that stage.
            if self.solve_cell.complete():
                solve.update(self.solve_cell.value())
            elif self.on("peak_fitting"):
                solve["cell_from"] = "peak_fitting"
            molecular = False
            if not cf:
                solve["structure"] = self.solve_kind.get()
                molecular = self.solve_kind.get() == "molecular"
                if molecular:
                    solve["fragment_source"] = self.zmat_source.get()
                    if self.zmat_source.get() == "file":
                        solve["fragment_file"] = as_posix(self.zmat_path.get().strip())
                    else:
                        solve["fragment_text"] = self.zmat_text.get("1.0", "end").strip()
            if not molecular:
                solve["empirical_formula"] = self.contents.get().strip()
                z = num_or_none(self.solve_z.get(), int)
                if z is not None:
                    solve["z"] = z
            job["solve"] = solve

        if self.on("rietveld"):
            # An untouched row is filler (§ is_blank), not a phase -- writing
            # it out invents a fake entry that then reloads as if someone had
            # named it, which is exactly what used to defeat is_blank() on
            # the next load and wrongly re-flag Riet forever after.
            real_rows = [r for r in self.phase_rows if not r.is_blank()]
            if real_rows:
                job["phases"] = [r.to_dict() for r in real_rows]

        # A modifier, not a stage: beside the list, never inside it.
        if self.on("seq_para"):
            job["sequential"] = {"mode": self.seq_mode.get(),
                                 "reel_output": self.seq_reel.get()}

        # Keys the Rietveld panel contributes are meaningless without it.
        if not self.on("rietveld"):
            for key in ("sample_size_strain", "rules", "first_cycle"):
                job.pop(key, None)
        # ToF has no slit correction, axial model or 2-theta offset.
        if tof:
            for key in ("variable_slits", "offset_correction",
                        "axial_length", "refine_axial"):
                job.pop(key, None)

        if extra:
            job["extra"] = extra
        return job

    def job_file_path(self, job: dict) -> Path:
        if self.out_override:
            return Path(self.out_override)
        out = Path(job["out"])
        return out.parent / f"{out.stem}_job.json"

    # -- actions -----------------------------------------------------------
    def on_ok(self):
        if not self.validate():
            return
        if self.mode.get() != "continue":
            out = Path(self.out_var.get().strip())
            if out.exists() and not self._resolve_collision(out):
                return
        try:
            job = self.collect()
            path = self.job_file_path(job)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(job, indent=2), encoding="utf-8")
            save_local({"last_job_path": str(path),
                        "general": {"last_dir": self._last_dir,
                                    "out_dir": str(Path(job["out"]).parent)}})
            self.job_path, self.exit_code = path, EXIT_OK
        except Exception:
            messagebox.showerror("TOPAS job wizard", traceback.format_exc())
            self.exit_code = EXIT_ERROR
        self.destroy()

    def _resolve_collision(self, out: Path) -> bool:
        """An existing output is very likely a refinement already in progress,
        and the in-place model means overwriting destroys its accumulated
        results. Continue is the intended route and the default."""
        dlg = tk.Toplevel(self)
        dlg.title("That file already exists")
        dlg.transient(self)
        ttk.Label(dlg, padding=12, wraplength=440, justify="left",
                  text=(f"{out.name} already exists.\n\n"
                        "It is very likely a refinement already in progress. The .inp "
                        "is the master file and accumulates results, so overwriting it "
                        "destroys them.")).pack()
        choice = {"v": None}

        def pick(v):
            choice["v"] = v
            dlg.destroy()

        bar = ttk.Frame(dlg, padding=(12, 0, 12, 12))
        bar.pack(fill="x")
        b = ttk.Button(bar, text="Continue that refinement", command=lambda: pick("continue"))
        b.pack(side="left")
        ttk.Button(bar, text="Next free suffix",
                   command=lambda: pick("suffix")).pack(side="left", padx=6)
        ttk.Button(bar, text="Overwrite", command=lambda: pick("overwrite")).pack(side="left")
        ttk.Button(bar, text="Cancel", command=dlg.destroy).pack(side="right")
        b.focus_set()
        dlg.bind("<Return>", lambda _e: pick("continue"))
        dlg.bind("<Escape>", lambda _e: dlg.destroy())
        dlg.grab_set()
        self.wait_window(dlg)

        if choice["v"] == "continue":
            self.mode.set("continue")
            self._on_mode()
            return True
        if choice["v"] == "suffix":
            self._sync_output_name()
            return True
        return choice["v"] == "overwrite"

    def on_save_defaults(self):
        """Save only fields the user actually set, or saving would convert every
        guess into an assertion."""
        patch = {"general": {"mode": self.mode.get()},
                 "rietveld": {"rules": self.rules.get()},
                 "measurement": {}, "corrections": {}, "peak_shape": {}}
        if self.slits.value() is not None:
            patch["measurement"]["variable_slits"] = self.slits.value()
        if self.offset.value() is not None:
            patch["corrections"]["offset_correction"] = self.offset.value()
        tmax = num_or_none(self.tmax.get())
        if tmax is not None:
            patch["corrections"]["two_theta_max"] = tmax
        if self.peak_shape.value() is not None:
            patch["peak_shape"]["model"] = self.peak_shape.value()
        patch["peak_shape"]["sample_size_strain"] = self.size_strain.get()
        save_local({k: v for k, v in patch.items() if v})
        messagebox.showinfo("TOPAS job wizard",
                            "Saved to wizard_defaults.local.json.\n\n"
                            "Only fields you set were saved.")

    def on_cancel(self):
        self.exit_code = EXIT_CANCEL
        self.destroy()

    def on_timeout(self):
        """Dump what is on screen before closing, so a slow user loses nothing."""
        try:
            job = self.collect()
            out = self.out_var.get().strip()
            if out:
                p = Path(out).parent / f"{Path(out).stem}_job.partial.json"
                p.write_text(json.dumps(job, indent=2), encoding="utf-8")
                print(f"timed out; partial job written to {p}", file=sys.stderr)
        except Exception:
            pass
        self.exit_code = EXIT_TIMEOUT
        self.destroy()


def natural_key(name: str):
    """Sort key that orders file_2 before file_10."""
    parts = re.split(r"(\d+)", name.lower())
    return [int(p) if p.isdigit() else p for p in parts]


def next_free_output(folder: Path, base: str, stages: list[str]) -> Path:
    """<base>_fit_NN.inp in the output folder. The suffix increments only for a
    NEW job; refinement cycles keep the name and update in place.

    The tag comes from the last stage that writes a fit, not from whichever tab
    is showing. A pipeline that ends at indexing gets _index_NN instead, and
    Solve never names the file.
    """
    folder = folder if str(folder) else Path.cwd()
    base = base or "refinement"
    tag = "fit" if any(s in FIT_STAGES for s in stages) else "index"
    n = 1
    while (folder / f"{base}_{tag}_{n:02d}.inp").exists():
        n += 1
    return folder / f"{base}_{tag}_{n:02d}.inp"


def claude_exe() -> str | None:
    """The Claude CLI's real path. npm installs it as claude.CMD, and
    CreateProcess resolves only .exe from a bare name, so the full path
    matters -- and it is run through cmd.exe, which is what can execute a
    .cmd at all."""
    for name in ("claude.cmd", "claude.exe", "claude"):
        found = shutil.which(name)
        if found:
            return found
    return None


def launch_claude(job_path: Path) -> str | None:
    """Hand one job file to a fresh Claude CLI session in its own console.
    Returns None on success, or a message to show the user.

    The job file's PATH is passed, never its contents: the Windows command
    line stops at 8191 characters and a 30-pattern job file is already ~4 kB,
    quite apart from escaping JSON through cmd.exe.
    """
    exe = claude_exe()
    if exe is None:
        return ("Claude CLI not found on PATH.\n\n"
                "The job file has been saved. Install the CLI, or open a "
                "terminal in that folder and run:\n\n"
                f"    claude \"/topilot-build {job_path.as_posix()}\"")

    # cwd is the job's home -- the folder the .inp goes in, which is where
    # every other file for this job also belongs.
    work_dir = job_path.parent
    prompt = f"/topilot-build {job_path.as_posix()}"
    # A literal string, not a list: Popen hands it to CreateProcess as-is on
    # Windows, so the quoting is exactly what is written here. /k keeps the
    # console open once Claude exits.
    #
    # The OUTER pair of quotes is cmd.exe's documented rule (cmd /?) for
    # "quoted program path plus quoted arguments"; without them cmd strips the
    # wrong quotes as soon as a path contains a space. They also re-expose the
    # prompt to cmd's parser, hence the ^-escaping below.
    safe = prompt
    for ch in "^&|<>()":
        safe = safe.replace(ch, "^" + ch)
    line = f'cmd.exe /k ""{exe}" "{safe}""'
    try:
        subprocess.Popen(line, cwd=str(work_dir),
                         creationflags=CREATE_NEW_CONSOLE)
    except Exception as exc:
        return f"Could not start the Claude CLI:\n\n{exc}"
    return None


def main(argv: list[str] | None = None, from_claude: bool | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="override the job file path (testing only)")
    ap.add_argument("--workflow", default="rietveld", help="which tab to open")
    ap.add_argument("--from-claude", action="store_true",
                    help="Claude Code is waiting on this process: print the "
                         "job file to stdout instead of starting a CLI session")
    ap.add_argument("--no-launch", action="store_true",
                    help="never start a CLI session, even standalone (testing)")
    args = ap.parse_args(argv)

    # Which of the two hand-offs OK performs -- is Claude Code DRIVING this
    # process?
    #   driven     -> write the job file, print it, exit 0; Claude reads stdout.
    #   standalone -> write the job file, open a Claude CLI session on it.
    # TOPilot.pyw passes from_claude=False. CLAUDECODE is a safety net so a bare
    # run inside a Claude session cannot spawn a stray terminal; --out and
    # --no-launch are the testing escapes.
    if from_claude is None:
        from_claude = (args.from_claude
                       or bool(os.environ.get("CLAUDECODE"))
                       or bool(args.out))
    if args.no_launch:
        from_claude = True

    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    try:
        app = Wizard(args.out, args.workflow, from_claude)
    except Exception:
        traceback.print_exc()
        return EXIT_ERROR

    app.mainloop()

    if app.exit_code != EXIT_OK or not app.job_path:
        return app.exit_code

    if from_claude:
        print(app.job_path)
        print(app.job_path.read_text(encoding="utf-8"))
        return EXIT_OK

    problem = launch_claude(app.job_path)
    if problem:
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("TOPilot wizard", problem)
            root.destroy()
        except Exception:
            print(problem, file=sys.stderr)
        return EXIT_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
