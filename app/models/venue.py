from dataclasses import dataclass


@dataclass
class Venue:
    id: int
    name: str
    total_stations: int


@dataclass
class VenueSector:
    id: int
    venue_id: int
    sector_name: str
    station_number: int
