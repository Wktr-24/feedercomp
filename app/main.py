import shutil
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

_BACKUPS_TO_KEEP = 5


def _backup_database(db_path: Path) -> None:
    """Copy data.db to backups/data-<timestamp>.db on every launch, keeping
    the newest few. A single mis-click (deleting day 1 of a two-day final
    cascades all its competitors) is otherwise unrecoverable in the field.
    Best-effort — a failed backup must never block startup."""
    if not db_path.exists():
        return
    try:
        backup_dir = db_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        shutil.copy2(db_path, backup_dir / f"data-{stamp}.db")
        for old in sorted(backup_dir.glob("data-*.db"))[:-_BACKUPS_TO_KEEP]:
            old.unlink()
    except OSError:
        pass


def _install_exception_handler(root) -> None:
    """The production build is windowed (no console), so an unhandled
    exception in a Tk callback would otherwise die silently — a button that
    'does nothing' with no trace. Log to error.log and tell the user where
    the details are."""
    log_path = get_data_dir() / "error.log"

    def _handler(exc_type, exc_value, exc_tb):
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(
                    f"\n--- {datetime.now().isoformat(timespec='seconds')} "
                    f"(FeederComp {__version__}) ---\n"
                )
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        except OSError:
            pass
        try:
            from tkinter import messagebox
            messagebox.showerror(
                "Błąd programu",
                "Wystąpił nieoczekiwany błąd:\n"
                f"{exc_type.__name__}: {exc_value}\n\n"
                f"Szczegóły zapisano w pliku:\n{log_path}",
            )
        except Exception:
            pass

    root.report_callback_exception = _handler


def main():
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
