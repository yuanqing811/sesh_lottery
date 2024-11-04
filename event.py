from enum import Enum
from dataclasses import dataclass


class EventType(Enum):
    CLINIC = 'clinic'
    ROUNDROBIN = 'round robin'
    OTHER = 'other'


class EventStatus(Enum):
    COMPLETED = 'completed'
    PRELOTTERY = 'prelottery'
    POSTLOTTERY = 'postlottery'
    CANCELLED = 'cancelled'

@dataclass
class Event:
    name: str
    event_type: str   # For example, "clinic", "round_robin", "dupr"
    start_datetime: str # Could be a string or datetime object
    end_datedate: str   # could be a string or datetime object
    min_dupr_rating: str
    max_dupr_rating: str


