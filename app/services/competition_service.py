import sqlite3
from dataclasses import dataclass

from app.repositories import competition_repo, competitor_repo
from app.utils import name_key


@dataclass
class Day2Result:
    competition_id: int
    copied_count: int
    # Names duplicated within the copied roster (possible only in rosters
    # entered before the duplicate guard existed). Reported at creation time
    # so the organizer can fix them before the final, not discover them on
    # the results screen.
    duplicate_names: list[str]


class Day2Error(Exception):
    """Raised when a day-2 competition cannot be created.

    `reason` is machine-readable; the UI maps it to a Polish message:
      - "source_missing":   the source competition does not exist
      - "source_is_day2":   the source is itself a day 2 (no day-3 chains)
      - "already_has_day2": the source already has a linked day 2
    """

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def create_day2(
    conn: sqlite3.Connection,
    source_competition_id: int,
    comp_date: str,
    name: str | None,
) -> Day2Result:
    """Create the day-2 competition of a two-day final: same venue, copied
    roster (list_number, full_name, phone, payment_status — presence,
    stations, weights and rankings start clean), linked to the source via
    linked_competition_id. Deliberately does NOT copy excluded_stations or
    competition_sector_overrides — those depend on that day's attendance.
    The copy is faithful even for duplicated legacy names (they are
    reported, not dropped). Commits.
    """
    source = competition_repo.get_by_id(conn, source_competition_id)
    if source is None:
        raise Day2Error("source_missing")
    if source.linked_competition_id is not None:
        raise Day2Error("source_is_day2")
    if competition_repo.get_day2_of(conn, source.id) is not None:
        raise Day2Error("already_has_day2")

    new_id = competition_repo.create(
        conn,
        source.venue_id,
        comp_date,
        name,
        max_competitors=source.max_competitors,
        winner_places=source.winner_places,
        linked_competition_id=source.id,
    )
    competitors = competitor_repo.get_all(conn, source.id)
    seen: dict[str, str] = {}
    duplicates: dict[str, str] = {}
    for c in competitors:
        competitor_repo.add(
            conn, new_id, c.list_number, c.full_name, c.phone, c.payment_status,
        )
        key = name_key(c.full_name)
        if key in seen:
            duplicates.setdefault(key, seen[key])
        else:
            seen[key] = c.full_name
    conn.commit()
    return Day2Result(
        competition_id=new_id,
        copied_count=len(competitors),
        duplicate_names=sorted(duplicates.values()),
    )
