import time

import customtkinter as ctk

from app.config import get_bundle_dir, get_db_path
from app.database import init_db
from app.ui.app_window import AppWindow
from app.utils import UNMAP_GRACE_SECONDS, set_window_icon


def main():
    db_path = get_db_path()
    init_db(db_path)

    theme_path = get_bundle_dir() / "app" / "themes" / "feederland.json"
    ctk.set_default_color_theme(str(theme_path))
    ctk.set_appearance_mode("dark")

    root = ctk.CTk()
    root.tk.eval('encoding system utf-8')

    from tkinter import ttk
    ttk.Style().theme_use("clam")
    root.title("FeederComp \u2013 Zawody W\u0119dkarskie")
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
