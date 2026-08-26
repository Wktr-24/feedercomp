import os
import re
import unicodedata

from app.config import get_bundle_dir

# How long after an <Unmap> we treat a <FocusIn> as a Win+D side-effect
# instead of a user-initiated restore. 1s is comfortably above the WM
# transition latency and well below human click-to-restore reaction time.
# Workaround for Tk bug ed6c3a787d / CPython #114422.
UNMAP_GRACE_SECONDS = 1.0


def set_window_icon(window) -> None:
    """Set the Feederland icon on a Tk window (root or Toplevel).

    Windows-only (uses .ico). No-op on other platforms or if icon missing.

    CTkToplevel.__init__ schedules TWO ``after(200, ...)`` callbacks that
    would overwrite our icon:
      - One calls ``_windows_set_titlebar_icon`` and is gated by the
        ``_iconbitmap_method_called`` flag (we set it here).
      - The other is an unconditional lambda calling ``self.iconbitmap(<CTk
        default>)`` (ctk_toplevel.py:45). It bypasses ``wm_iconbitmap``
        entirely. ``FeederCompDialog`` therefore overrides ``iconbitmap``
        and consults a per-window ``_user_icon_set`` flag that we set here
        — late CTk calls are then no-ops.

    Avoiding our previous ``after(250)`` re-apply also keeps Win32 from
    rebuilding the toplevel frame after the transient owner-chain has been
    wired up, which used to leave the root window un-restorable from the
    taskbar after Win+D.
    """
    if os.name != 'nt':
        return
    icon_path = get_bundle_dir() / "assets" / "feederland-favicon.ico"
    if not icon_path.exists():
        return
    try:
        window.wm_iconbitmap(str(icon_path))
        if hasattr(window, '_iconbitmap_method_called'):
            window._iconbitmap_method_called = True
        window._user_icon_set = True
    except Exception:
        pass


def name_key(text: str) -> str:
    """Canonical identity key for a competitor name: Unicode-NFC-normalized,
    whitespace-normalized and case-folded. Used both for duplicate detection
    within a competition and for pairing competitors across the two days of
    a final — the two must agree, or a name the duplicate guard allows could
    still be ambiguous to the pairing logic. NFC folds precomposed and
    combining-diacritic spellings (e.g. "ó" vs "o"+U+0301) into one key so a
    name pasted from another source still pairs.
    """
    # (NFC first, then casefold — the fold of exotic codepoints can emit
    # non-NFC output, but both sides of every comparison fold identically,
    # so pairing is unaffected.)
    return unicodedata.normalize("NFC", normalize_whitespace(text)).casefold()


def parse_strict_iso_date(text: str):
    """Parse a date accepting ONLY the canonical YYYY-MM-DD form; None otherwise.

    Both datetime.strptime("%Y-%m-%d") and date.fromisoformat are laxer than
    they look: strptime accepts unpadded "2026-9-5", and fromisoformat (3.11+)
    accepts "20260905" and week dates like "2026-W36-1". Any such value stored
    in competitions.date breaks date-DESC sorting and the PDF date formatting,
    so validate by round-trip.
    """
    from datetime import date
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == text else None


def normalize_whitespace(text: str) -> str:
    """Collapse multiple whitespace to single space and strip edges.

    Examples:
        "  Liga   Karpiowa  " -> "Liga Karpiowa"
        "Jan\tKowalski" -> "Jan Kowalski"
    """
    return re.sub(r'\s+', ' ', text).strip()


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
