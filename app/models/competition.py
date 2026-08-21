from dataclasses import dataclass
from typing import Optional


@dataclass
class Competition:
    id: int
    venue_id: int
    date: str
    name: Optional[str] = None
    max_competitors: int = 50
    winner_places: int = 3
    created_at: Optional[str] = None
    # Set on a day-2 competition of a two-day final: points at its day-1.
    linked_competition_id: Optional[int] = None
