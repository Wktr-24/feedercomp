import sqlite3
import time
import traceback
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from app import __version__
from app.config import get_bundle_dir, get_data_dir, get_db_path
from app.database import init_db
from app.ui.app_window import AppWindow
from app.utils import UNMAP_GRACE_SECONDS, set_window_icon

# 20 launches of history (~85 KB each): a two-day final easily sees a dozen
# restarts, and 5 would rotate the pre-incident snapshot away within an hour.
_BACKUPS_TO_KEEP = 20

_ERROR_LOG_PATH = get_data_dir() / "error.log"


def _backup_database(db_path: Path) -> None:
    """Snapshot data.db to backups/data-<timestamp>.db on every launch,
    keeping the newest _BACKUPS_TO_KEEP. A single mis-click (deleting day 1
    of a two-day final cascades all its competitors) is otherwise
    unrecoverable in the field. Uses SQLite's backup API instead of a file
    copy so a hot journal left by a crash is folded in consistently.
    Best-effort — a failed backup must never block startup."""
    if not db_path.exists():
        return
    try:
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        src = sqlite3.connect(str(db_path))
        try:
            dst = sqlite3.connect(str(backup_dir / f"data-{stamp}.db"))
            try:
                src.backup(dst)
            finally:
                dst.close()
        finally:
            src.close()
        # Prune only files matching the timestamp shape — a hand-made copy
        # like data-przed-finalem.db must never take part in the rotation.
        stamped = sorted(backup_dir.glob("data-????????-??????.db"))
        for old in stamped[:-_BACKUPS_TO_KEEP]:
            old.unlink()
    except (OSError, sqlite3.Error):
        pass


def _log_exception(exc_type, exc_value, exc_tb) -> None:
    try:
        with open(_ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(
                f"\n--- {datetime.now().isoformat(timespec='seconds')} "
                f"(FeederComp {__version__}) ---\n"
            )
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        # Even a hostile __str__ on the exception must not re-raise here —
        # that would restore the silent-failure mode this exists to remove.
        pass


def _install_exception_handler(root) -> None:
    """The production build is windowed (no console), so an unhandled
    exception in a Tk callback would otherwise die silently — a button that
    'does nothing' with no trace. Log to error.log and tell the user where
    the details are. The messagebox shows at most once per session: a
    repeating exception in an event handler (<Configure>, after-loops) would
    otherwise stack modal boxes faster than they can be closed."""
    shown = {"box": False}

    def _handler(exc_type, exc_value, exc_tb):
        _log_exception(exc_type, exc_value, exc_tb)
        if shown["box"]:
            return
        shown["box"] = True
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Błąd programu",
                "Wystąpił nieoczekiwany błąd:\n"
                f"{exc_type.__name__}: {exc_value}\n\n"
                f"Szczegóły zapisano w pliku:\n{_ERROR_LOG_PATH}\n\n"
                "(Kolejne błędy w tej sesji będą zapisywane tylko do pliku.)",
                parent=root.grab_current() or root,
            )
        except Exception:
            pass

    root.report_callback_exception = _handler


def main():
    # Startup crashes (a bad migration, a corrupted DB, missing bundle data)
    # happen before Tk exists, so report_callback_exception can't see them.
    # PyInstaller's windowed bootloader shows its own traceback box, but
    # nothing would be written to error.log — log here, then re-raise.
    try:
        _run()
    except Exception:
        import sys
        _log_exception(*sys.exc_info())
        raise


def _run():
    db_path = get_db_path()
    _backup_database(db_path)
    init_db(db_path)

    theme_path = get_bundle_dir() / "app" / "themes" / "feederland.json"
    ctk.set_default_color_theme(str(theme_path))
    ctk.set_appearance_mode("dark")

    root = ctk.CTk()
    root.tk.eval('encoding system utf-8')
    _install_exception_handler(root)

    from tkinter import ttk
    ttk.Style().theme_use("clam")
    root.title(f"FeederComp {__version__} \u2013 Zawody W\u0119dkarskie")
    root.geometry("1100x700")
    root.minsize(900, 600)

    set_window_icon(root)

    # Workaround for Tk bug ed6c3a787d / CPython #114422. Same time-based
    # debounce as in FeederCompDialog: only treat <FocusIn> as a restore
    # request when it arrives well after the last <Unmap> (real user click,
    # not the Win+D transient focus race). Initialise far in the past so
    # the first <FocusIn> at startup is never treated as a Win+D race.
    root._last_unmap_time = float("-inf")

    def _on_root_unmap(_event):
        root._last_unmap_time = time.monotonic()

    def _restore_root_if_unmapped(_event):
        if root.winfo_ismapped():
            return
        if time.monotonic() - root._last_unmap_time < UNMAP_GRACE_SECONDS:
            return
        try:
            root.deiconify()
        except Exception:
            pass

    root.bind("<Unmap>", _on_root_unmap, add="+")
    root.bind("<FocusIn>", _restore_root_if_unmapped, add="+")

    app = AppWindow(root, db_path)
    app.pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
