"""TOPilot wizard — double-clickable launcher.

Runs the same dialog as topilot_wizard.py, but standalone: on OK it opens a
Claude CLI session on the job file it just wrote, instead of printing the job
to stdout for a waiting Claude Code call.

.pyw so Windows runs it under pythonw.exe with no console window. The wizard
itself stays a plain .py, which keeps it importable and gives it a console
when it is run for testing.

The whole body is wrapped: under pythonw.exe there is no console, so an
uncaught traceback would vanish silently. It goes to a log file beside this
one, and a message box says where.
"""
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def report(message: str):
    """Say something when there is no console to say it to."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("TOPilot wizard", message)
        root.destroy()
    except Exception:
        pass


try:
    import topilot_wizard
except Exception:
    log = HERE / "topilot_wizard_crash.log"
    try:
        log.write_text(traceback.format_exc(), encoding="utf-8")
        where = f"\n\nDetails written to:\n{log}"
    except Exception:
        where = "\n\n" + traceback.format_exc()
    report("Could not load topilot_wizard.py." + where)
    sys.exit(1)

try:
    # from_claude=False regardless of the environment: double-clicking this is
    # an explicit request for the CLI hand-off.
    sys.exit(topilot_wizard.main(argv=[], from_claude=False))
except SystemExit:
    raise
except Exception:
    log = HERE / "topilot_wizard_crash.log"
    try:
        log.write_text(traceback.format_exc(), encoding="utf-8")
        where = f"\n\nDetails written to:\n{log}"
    except Exception:
        where = "\n\n" + traceback.format_exc()
    report("The TOPilot wizard stopped with an error." + where)
    sys.exit(1)
