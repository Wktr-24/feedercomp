"""Generate an A3 landscape PDF diagram of a fishing venue layout.

Reads venue configuration from seed_data/venues.json and draws a schematic
view of the pond with numbered stations arranged along top and bottom banks,
sectors labeled inside a blue rectangle representing the water, separated
by red vertical lines.

Usage:
    python scripts/generate_pond_diagram.py [venue_name]

Default venue_name is "Stawy Siedleckie".
Output file: Schemat_<venue_name>.pdf in the project root.
"""
import json
import os
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VENUES_JSON = PROJECT_ROOT / "seed_data" / "venues.json"

POND_COLOR = colors.HexColor("#1a5276")
SEPARATOR_COLOR = colors.HexColor("#E74C3C")
STATION_FILL = colors.HexColor("#F5B041")
STATION_BORDER = colors.HexColor("#7E5109")
STATION_TEXT = colors.HexColor("#1B2631")

_FONT_CANDIDATES = [
    (
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arialbd.ttf"),
    ),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ),
    (
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ),
]

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def register_fonts():
    global FONT_REGULAR, FONT_BOLD
    for regular_path, bold_path in _FONT_CANDIDATES:
        if os.path.exists(regular_path) and os.path.exists(bold_path):
            pdfmetrics.registerFont(TTFont("DiagramSans", regular_path))
            pdfmetrics.registerFont(TTFont("DiagramSans-Bold", bold_path))
            FONT_REGULAR = "DiagramSans"
            FONT_BOLD = "DiagramSans-Bold"
            return
    print(
        "OSTRZEŻENIE: Nie znaleziono czcionek TTF z obsługą polskich znaków. "
        "Używam Helvetica — polskie znaki mogą się źle wyświetlać.",
        file=sys.stderr,
    )


def load_venue(venue_name: str) -> dict:
    with open(VENUES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    for venue in data["venues"]:
        if venue["name"] == venue_name:
            if not venue.get("sectors"):
                raise ValueError(
                    f"Łowisko '{venue_name}' nie ma skonfigurowanych sektorów."
                )
            return venue
    available = ", ".join(v["name"] for v in data["venues"])
    raise ValueError(
        f"Nie znaleziono łowiska '{venue_name}'. Dostępne: {available}"
    )


def split_top_bottom(stations: list[int], venue: dict) -> tuple[list[int], list[int]]:
    """Split a sector's stations into (top, bottom) banks, left-to-right.

    If the venue declares explicit ``banks``, follow that ordering. Otherwise
    fall back to the heuristic: stations <= half on top (desc), > half on
    bottom (asc).
    """
    banks = venue.get("banks")
    if banks:
        sset = set(stations)
        top = [s for s in banks["top"] if s in sset]
        bottom = [s for s in banks["bottom"] if s in sset]
        return top, bottom
    half = venue["total_stations"] // 2
    top = sorted([s for s in stations if s <= half], reverse=True)
    bottom = sorted([s for s in stations if s > half])
    return top, bottom


def draw_station(c: canvas.Canvas, x: float, y: float, size: float, number: int):
    c.setFillColor(STATION_FILL)
    c.setStrokeColor(STATION_BORDER)
    c.setLineWidth(0.8)
    c.roundRect(x, y, size, size, radius=1.5*mm, stroke=1, fill=1)
    c.setFillColor(STATION_TEXT)
    c.setFont(FONT_BOLD, 11)
    text = str(number)
    text_width = c.stringWidth(text, FONT_BOLD, 11)
    c.drawString(x + (size - text_width) / 2, y + size / 2 - 3.5, text)


def effective_sectors(venue: dict, variant: dict | None) -> dict[str, list[int]]:
    """Apply a balance variant to the venue's base sector map.

    ``sector_overrides`` moves a station to another sector (e.g. Lasomin
    variant 2: station 13 from C to D). ``excluded`` stations are dropped
    entirely. variant=None returns the full (komplet) configuration.
    """
    sectors = {name: list(st) for name, st in venue["sectors"].items()}
    if not variant:
        return sectors
    for st_str, target in variant.get("sector_overrides", {}).items():
        st = int(st_str)
        for name in sectors:
            if st in sectors[name]:
                sectors[name].remove(st)
        sectors.setdefault(target, []).append(st)
    excluded = set(variant.get("excluded", []))
    for name in sectors:
        sectors[name] = [s for s in sectors[name] if s not in excluded]
    return sectors


def generate(
    venue_name: str,
    variant: dict | None = None,
    label: str = "",
    suffix: str = "",
) -> Path:
    register_fonts()
    venue = load_venue(venue_name)

    sectors_map = effective_sectors(venue, variant)
    sector_names = sorted(sectors_map.keys(), reverse=True)
    num_sectors = len(sector_names)
    sectors_lr = [
        {"name": name, "stations": sorted(sectors_map[name])}
        for name in sector_names
    ]
    total_stations = sum(len(sec["stations"]) for sec in sectors_lr)

    output_file = PROJECT_ROOT / f"Schemat_{venue_name.replace(' ', '_')}{suffix}.pdf"
    page_w, page_h = landscape(A3)
    c = canvas.Canvas(str(output_file), pagesize=landscape(A3))
    c.setTitle(f"Schemat łowiska — {venue_name}")

    # --- Title ---
    c.setFillColor(colors.black)
    c.setFont(FONT_BOLD, 22)
    title = f"Schemat łowiska: {venue_name}"
    title_w = c.stringWidth(title, FONT_BOLD, 22)
    c.drawString((page_w - title_w) / 2, page_h - 20*mm, title)

    c.setFont(FONT_REGULAR, 14)
    subtitle = f"{total_stations} stanowisk, {num_sectors} sektorów"
    if label:
        subtitle = f"{label}  —  {subtitle}"
    subtitle_w = c.stringWidth(subtitle, FONT_REGULAR, 14)
    c.drawString((page_w - subtitle_w) / 2, page_h - 30*mm, subtitle)

    # --- Layout geometry ---
    margin = 15*mm
    area_x = margin
    area_y = margin
    area_w = page_w - 2 * margin
    top_of_content = page_h - 40*mm

    pond_height = 55*mm
    bank_height = 22*mm
    gap = 4*mm

    content_h = bank_height + gap + pond_height + gap + bank_height
    content_top = top_of_content - (top_of_content - area_y - content_h) / 2
    top_bank_y = content_top - bank_height
    pond_y = top_bank_y - gap - pond_height
    bottom_bank_y = pond_y - gap - bank_height

    sector_width = area_w / num_sectors
    splits = [split_top_bottom(sec["stations"], venue) for sec in sectors_lr]
    max_stations_per_sector_side = max(
        max(len(top), len(bottom)) for top, bottom in splits
    )
    station_size = min(
        bank_height - 2*mm,
        (sector_width - 4*mm) / max_stations_per_sector_side - 1*mm,
    )
    station_spacing = 1.5*mm

    # --- Pond rectangle: hollow outline only (printer-friendly) ---
    c.setStrokeColor(POND_COLOR)
    c.setLineWidth(3)
    c.rect(area_x, pond_y, area_w, pond_height, stroke=1, fill=0)

    # Sector labels inside pond (dark text on white background)
    c.setFillColor(STATION_TEXT)
    for i, sec in enumerate(sectors_lr):
        cx = area_x + i * sector_width + sector_width / 2
        c.setFont(FONT_BOLD, 18)
        label = f"Sektor {sec['name']}"
        label_w = c.stringWidth(label, FONT_BOLD, 18)
        c.drawString(cx - label_w / 2, pond_y + pond_height / 2 + 2, label)
        c.setFont(FONT_REGULAR, 12)
        count_text = f"({len(sec['stations'])} stanowisk)"
        count_w = c.stringWidth(count_text, FONT_REGULAR, 12)
        c.drawString(cx - count_w / 2, pond_y + pond_height / 2 - 12, count_text)

    # Red separators between sectors
    c.setStrokeColor(SEPARATOR_COLOR)
    c.setLineWidth(2)
    for i in range(1, num_sectors):
        sep_x = area_x + i * sector_width
        c.line(sep_x, pond_y, sep_x, pond_y + pond_height)

    # --- Top and bottom banks ---
    for i, sec in enumerate(sectors_lr):
        top, bottom = splits[i]
        sector_center_x = area_x + i * sector_width + sector_width / 2

        total_top_w = len(top) * station_size + (len(top) - 1) * station_spacing
        top_start_x = sector_center_x - total_top_w / 2
        for j, station in enumerate(top):
            sx = top_start_x + j * (station_size + station_spacing)
            sy = top_bank_y + (bank_height - station_size) / 2
            draw_station(c, sx, sy, station_size, station)

        total_bot_w = len(bottom) * station_size + (len(bottom) - 1) * station_spacing
        bot_start_x = sector_center_x - total_bot_w / 2
        for j, station in enumerate(bottom):
            sx = bot_start_x + j * (station_size + station_spacing)
            sy = bottom_bank_y + (bank_height - station_size) / 2
            draw_station(c, sx, sy, station_size, station)

    c.showPage()
    c.save()
    return output_file


def variant_label(num_missing: int, variant: dict) -> str:
    excluded = sorted(variant.get("excluded", []))
    excl = ", ".join(str(s) for s in excluded)
    competitor_word = "zawodnika" if num_missing == 1 else "zawodników"
    station_word = "stanowisko" if len(excluded) == 1 else "stanowiska"
    return (
        f"Brak {num_missing} {competitor_word} "
        f"(wykluczone {station_word}: {excl})"
    )


def main():
    venue_name = sys.argv[1] if len(sys.argv) > 1 else "Stawy Siedleckie"
    try:
        venue = load_venue(venue_name)
        variants = venue.get("balance_variants")
        if variants:
            jobs = [(None, "Komplet", "_komplet")]
            for key in sorted(variants, key=int):
                v = variants[key]
                jobs.append((v, variant_label(int(key), v), f"_brak-{key}"))
        else:
            jobs = [(None, "", "")]
        for v, label, suffix in jobs:
            path = generate(venue_name, v, label, suffix)
            print(f"Wygenerowano: {path}")
    except ValueError as e:
        print(f"Błąd: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
