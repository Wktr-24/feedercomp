from dataclasses import dataclass
from typing import Optional


@dataclass
class Competitor:
    id: int
    competition_id: int
    list_number: int
    full_name: str
    phone: Optional[str] = None
    payment_status: str = 'unpaid'
    is_present: bool = False
    station_number: Optional[int] = None
    sector_name: Optional[str] = None
    weight_grams: int = 0
    sector_place: Optional[int] = None
    sector_points: Optional[int] = None
    final_place: Optional[int] = None
