import os
import tempfile
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONT_DIR = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
pdfmetrics.registerFont(TTFont('Arial', os.path.join(_FONT_DIR, 'arial.ttf')))
pdfmetrics.registerFont(TTFont('Arial-Bold', os.path.join(_FONT_DIR, 'arialbd.ttf')))


class PrintService:
    def __init__(self):
        self.output_dir = Path(tempfile.gettempdir()) / "FeederComp"
        self.output_dir.mkdir(exist_ok=True)

    def _format_weight_kg(self, grams: int) -> str:
        if grams == 0:
            return "0"
        return f"{grams / 1000:.3f}".replace(".", ",")

    def _build_header(self, venue_name: str, comp_date: str, comp_name: str | None) -> list:
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontName='Arial-Bold',
            fontSize=16,
            alignment=TA_CENTER,
            spaceAfter=2*mm,
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontName='Arial',
            fontSize=12,
            alignment=TA_CENTER,
            spaceAfter=2*mm,
        )

        elements = []
        elements.append(Paragraph("WKS FEEDERLAND", title_style))

        try:
            parts = comp_date.split("-")
            display_date = f"{parts[2]}.{parts[1]}.{parts[0]}"
        except (IndexError, AttributeError):
            display_date = comp_date

        date_text = f"ZAWODY {display_date}"
        if comp_name:
            date_text = f"{comp_name} — {display_date}"
        elements.append(Paragraph(date_text, subtitle_style))
        elements.append(Paragraph(f"Łowisko {venue_name.upper()}", subtitle_style))
        elements.append(Spacer(1, 5*mm))

        return elements

    def _table_style(self) -> TableStyle:
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2B5797')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Arial-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Arial'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0F0F0')]),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ])

    def generate_sector_pdf(self, conn, competition_id: int, sector_name: str,
                            venue_name: str, comp_date: str, comp_name: str | None) -> Path:
        from app.repositories import competitor_repo

        filepath = self.output_dir / f"Sektor_{sector_name}.pdf"
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=15*mm, bottomMargin=15*mm)

        elements = self._build_header(venue_name, comp_date, comp_name)

        styles = getSampleStyleSheet()
        sector_style = ParagraphStyle('SectorTitle', parent=styles['Heading2'],
                                       fontName='Arial-Bold', alignment=TA_CENTER, fontSize=14)
        elements.append(Paragraph(f"Sektor {sector_name}", sector_style))
        elements.append(Spacer(1, 3*mm))

        data = [['STANOWISKO', 'ZAWODNIK', 'WAGA (kg)', 'MIEJSCE']]
        competitors = competitor_repo.get_by_sector(conn, competition_id, sector_name)
        competitors.sort(key=lambda c: c.station_number or 0)

        for c in competitors:
            place = str(c.sector_place) if c.sector_place is not None else ""
            data.append([
                str(c.station_number or ""),
                c.full_name,
                self._format_weight_kg(c.weight_grams),
                place,
            ])

        col_widths = [70, 200, 80, 70]
        table = Table(data, colWidths=col_widths)
        table.setStyle(self._table_style())
        elements.append(table)

        doc.build(elements)
        return filepath

    def generate_classification_pdf(self, conn, competition_id: int,
                                     venue_name: str, comp_date: str, comp_name: str | None) -> Path:
        from app.repositories import competitor_repo

        filepath = self.output_dir / "Klasyfikacja_koncowa.pdf"
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=15*mm, bottomMargin=15*mm)

        elements = self._build_header(venue_name, comp_date, comp_name)

        styles = getSampleStyleSheet()
        title = ParagraphStyle('ClassTitle', parent=styles['Heading2'],
                                fontName='Arial-Bold', alignment=TA_CENTER, fontSize=14)
        elements.append(Paragraph("KLASYFIKACJA KOŃCOWA", title))
        elements.append(Spacer(1, 3*mm))

        data = [['MIEJSCE', 'IMIĘ I NAZWISKO', 'SEKTOR', 'PKT SEKT.', 'WAGA (kg)']]
        competitors = competitor_repo.get_all(conn, competition_id)

        with_place = sorted([c for c in competitors if c.final_place is not None], key=lambda c: c.final_place)
        without_place = sorted(
            [c for c in competitors if c.final_place is None],
            key=lambda c: (c.sector_name is None, c.sector_name or "", c.list_number),
        )

        for c in with_place + without_place:
            place = str(c.final_place) if c.final_place is not None else "-"
            data.append([
                place,
                c.full_name,
                c.sector_name or "",
                str(c.sector_points) if c.sector_points is not None else "",
                self._format_weight_kg(c.weight_grams),
            ])

        col_widths = [55, 200, 55, 70, 80]
        table = Table(data, colWidths=col_widths)
        table.setStyle(self._table_style())
        elements.append(table)

        doc.build(elements)
        return filepath

    def generate_winners_pdf(self, conn, competition_id: int, winner_places: int,
                              venue_name: str, comp_date: str, comp_name: str | None) -> Path:
        from app.services.ranking_service import RankingService
        from app.services.sector_service import SectorService

        filepath = self.output_dir / "Lista_zwyciezcow.pdf"
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                                leftMargin=15*mm, rightMargin=15*mm,
                                topMargin=15*mm, bottomMargin=15*mm)

        elements = self._build_header(venue_name, comp_date, comp_name)

        styles = getSampleStyleSheet()
        title = ParagraphStyle('WinnersTitle', parent=styles['Heading2'],
                                fontName='Arial-Bold', alignment=TA_CENTER, fontSize=14)
        elements.append(Paragraph("ZWYCIĘZCY — NAGRODZENI", title))
        elements.append(Spacer(1, 3*mm))

        service = RankingService(SectorService())
        winners = service.get_winners(conn, competition_id, winner_places)

        data = [['MIEJSCE', 'IMIĘ I NAZWISKO', 'WAGA (kg)']]
        for c in winners:
            data.append([
                str(c.final_place) if c.final_place is not None else "-",
                c.full_name,
                self._format_weight_kg(c.weight_grams),
            ])

        col_widths = [60, 250, 100]
        table = Table(data, colWidths=col_widths)
        table.setStyle(self._table_style())
        elements.append(table)

        doc.build(elements)
        return filepath

    def open_pdf(self, filepath: Path):
        if os.name == 'nt':
            os.startfile(filepath)
        else:
            import subprocess
            subprocess.Popen(['xdg-open', str(filepath)])
