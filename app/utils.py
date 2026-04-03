def format_weight_kg(grams: int) -> str:
    if grams == 0:
        return "0"
    return f"{grams / 1000:.3f}".replace(".", ",")


def configure_treeview_style():
    from tkinter import ttk

    style = ttk.Style()
    style.configure("Treeview", font=("Segoe UI", 13), rowheight=28)
    style.configure("Treeview.Heading", font=("Segoe UI", 13, "bold"))
