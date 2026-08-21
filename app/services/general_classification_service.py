"""Two-day general classification for the season final.

Rules (locked with the organizer, call of 2026-08-20):
  - Day 1 and day 2 are two separate competitions linked via
    competitions.linked_competition_id (day 2 points at day 1).
  - Only competitors who took part in BOTH days are classified; anyone
    present on a single day is omitted entirely ("taka osoba nas nie
    interesuje"). "Took part on a day" = has a station/sector assigned
    (sector_name is not None — the same convention print_service and
    results_screen use), plus computed sector_points.
  - Rank by total sector points (both days) ascending, ties broken by
    total weight (both days) descending; full ties share a place,
    competition-style 1, 2, 2, 4.
  - Total weight 0 (caught nothing on either day) -> no place, listed
    after the scored rows, rendered "-" — consistent with the daily
    classification's zero-weight rule.
  - Competitors are paired across days by normalized, case-folded
    full_name (the only cross-competition identity that exists). Any
    name that appears more than once within either day is ambiguous:
    those competitors are excluded from the table and reported in
    `duplicate_names` so the organizer can disambiguate and recalculate
    — never silently mispair at a live event.

Read-only: nothing is persisted. Fresh per-day points are the caller's
responsibility (ResultsScreen recalculates both days before rendering).
"""
import sqlite3
from dataclasses import dataclass
from typing import Optional

from app.models.competition import Competition
from app.repositories import competition_repo, competitor_repo
from app.utils import normalize_whitespace


@dataclass
class GeneralRow:
    full_name: str
    points_day1: int
    points_day2: int
    total_points: int
    weight_day1: int
    weight_day2: int
    total_weight_grams: int
    place: Optional[int]


@dataclass
class GeneralClassification:
    rows: list[GeneralRow]
    duplicate_names: list[str]


def resolve_linked_pair(
    conn: sqlite3.Connection, competition_id: int,
) -> tuple[Competition, Competition] | None:
    """Return (day1, day2) for a linked two-day pair that `competition_id`
    belongs to — from either side of the link — or None."""
    comp = competition_repo.get_by_id(conn, competition_id)
    if comp is None:
        return None
    if comp.linked_competition_id is not None:
        day1 = competition_repo.get_by_id(conn, comp.linked_competition_id)
        if day1 is None:
            return None
        return day1, comp
    day2 = competition_repo.get_day2_of(conn, competition_id)
    if day2 is None:
        return None
    return comp, day2


def _normalize(name: str) -> str:
    return normalize_whitespace(name).casefold()


def _participants_by_key(conn, competition_id):
    """Map normalized name -> competitor for everyone who took part that day.
    Second return value: display names of keys that appear more than once."""
    by_key: dict[str, object] = {}
    duplicate_display: dict[str, str] = {}
    for c in competitor_repo.get_all(conn, competition_id):
        if c.sector_name is None or c.sector_points is None:
            continue
        key = _normalize(c.full_name)
        if key in by_key:
            duplicate_display.setdefault(key, by_key[key].full_name)
        else:
            by_key[key] = c
    return by_key, duplicate_display


def calculate(
    conn: sqlite3.Connection, day1_id: int, day2_id: int,
) -> GeneralClassification:
    day1_by_key, dup1 = _participants_by_key(conn, day1_id)
    day2_by_key, dup2 = _participants_by_key(conn, day2_id)

    duplicate_display = {**dup2, **dup1}
    for key in duplicate_display:
        day1_by_key.pop(key, None)
        day2_by_key.pop(key, None)
    duplicate_names = sorted(duplicate_display.values())

    rows: list[GeneralRow] = []
    for key, c1 in day1_by_key.items():
        c2 = day2_by_key.get(key)
        if c2 is None:
            continue
        rows.append(
            GeneralRow(
                full_name=c1.full_name,
                points_day1=c1.sector_points,
                points_day2=c2.sector_points,
                total_points=c1.sector_points + c2.sector_points,
                weight_day1=c1.weight_grams,
                weight_day2=c2.weight_grams,
                total_weight_grams=c1.weight_grams + c2.weight_grams,
                place=None,
            )
        )

    scored = [r for r in rows if r.total_weight_grams > 0]
    zero = [r for r in rows if r.total_weight_grams == 0]

    scored.sort(key=lambda r: (r.total_points, -r.total_weight_grams))
    place = 0
    for i, r in enumerate(scored):
        if i == 0 or (r.total_points, r.total_weight_grams) != (
            scored[i - 1].total_points, scored[i - 1].total_weight_grams,
        ):
            place = i + 1
        r.place = place

    zero.sort(key=lambda r: r.full_name)
    return GeneralClassification(rows=scored + zero, duplicate_names=duplicate_names)
