import customtkinter as ctk

from app.config import get_bundle_dir, get_db_path
from app.database import init_db
from app.ui.app_window import AppWindow


def main():
    db_path = get_db_path()
    init_db(db_path)

    theme_path = get_bundle_dir() / "app" / "themes" / "feederland.json"
    ctk.set_default_color_theme(str(theme_path))
    ctk.set_appearance_mode("dark")

    root = ctk.CTk()

    from tkinter import ttk
    ttk.Style().theme_use("clam")
    root.title("FeederComp \u2013 Zawody W\u0119dkarskie")
    root.geometry("1100x700")
    root.minsize(900, 600)

    app = AppWindow(root, db_path)
    app.pack(fill="both", expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
