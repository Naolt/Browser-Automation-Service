from enum import Enum
from typing import Optional
from pydantic import BaseModel

class ReservationMethod(str, Enum):
    GOOGLE_RESERVE = "google_reserve"
    FIND_TABLE_BUTTON = "find_table_button"
    FIND_TABLE_LINK = "find_table_link"
    DIRECT_PROVIDER = "direct_provider"

class ProviderType(str, Enum):
    SEVENROOMS = "sevenrooms"
    OPENTABLE = "opentable"
    GOOGLE = "google"
    UNKNOWN = "unknown"

class ReservationOption(BaseModel):
    provider: ProviderType
    href: Optional[str] = None
    selector: Optional[str] = None
    is_button: bool = False
    is_link: bool = False
