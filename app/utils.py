def format_weight_kg(grams: int) -> str:
    if grams == 0:
        return "0"
    return f"{grams / 1000:.3f}".replace(".", ",")


def configure_treeview_style(dark_mode: bool = True):
    from tkinter import ttk

    style = ttk.Style()
    if dark_mode:
        style.configure("Treeview",
            font=("Segoe UI", 14),
            rowheight=28,
            background="#2B2B2B",
            foreground="#FFFFFF",
            fieldbackground="#2B2B2B",
        )
        style.configure("Treeview.Heading",
            font=("Segoe UI", 14, "bold"),
            background="#3A3A3A",
            foreground="#FFFFFF",
        )
        style.map("Treeview",
            background=[("selected", "#DBA804")],
            foreground=[("selected", "#1A1A1A")],
        )
        style.map("Treeview.Heading",
            background=[("active", "#4A4A4A")],
        )
    else:
        style.configure("Treeview",
            font=("Segoe UI", 14),
            rowheight=28,
            background="#FFFFFF",
            foreground="#000000",
            fieldbackground="#FFFFFF",
        )
        style.configure("Treeview.Heading",
            font=("Segoe UI", 14, "bold"),
            background="#E8E8E8",
            foreground="#000000",
        )
        style.map("Treeview",
            background=[("selected", "#DBA804")],
            foreground=[("selected", "#1A1A1A")],
        )
        style.map("Treeview.Heading",
            background=[("active", "#D0D0D0")],
        )


def get_treeview_tag_colors(dark_mode: bool = True) -> dict:
    if dark_mode:
        return {
            "even": "#2B2B2B",
            "odd": "#333333",
            "reserve": "#4A3A00",
        }
    else:
        return {
            "even": "#FFFFFF",
            "odd": "#F0F0F0",
            "reserve": "#FFF3CD",
        }
