from abc import ABC, abstractmethod
import re
from typing import Optional
from browser_use import ActionResult, BrowserSession
from browser_use.browser.types import Page
from models.reservation_models import ProviderType, ReservationOption
from services.actions import controller
from services.actions.utils import build_reservation_failure_message, RESERVATION_ERRORS
import logging
logging.basicConfig(level=logging.INFO, filename="manual_reservation.log")
logger = logging.getLogger(__name__)

class BaseReservationProvider(ABC):
    """
    Base class for all reservation providers.
    Each provider should inherit from this class and implement the required methods.
    """
    
    def __init__(self, provider_name: str, url_prefixes: list[str], provider_type: ProviderType, discovery_patterns: list[str]):
        self.provider_name = provider_name
        self.url_prefixes = url_prefixes
        self.provider_type = provider_type
        self.discovery_patterns = discovery_patterns

    def log_message(self, message: str):    
        logger.info(f"[{self.provider_name}] {message}")    
    
    def is_valid_url(self, url: str) -> bool:
        """Check if the URL is valid for this provider."""
        return any(url.startswith(prefix) for prefix in self.url_prefixes)

    async def discover_reservation_option(self, page) -> Optional[ReservationOption]:
        # Search all links with matching patterns in href or text
        elements = page.locator("a")
        for i in range(await elements.count()):
            el = elements.nth(i)
            href = await el.get_attribute("href") or ""
            text = (await el.inner_text()).lower()
            combined = f"{href} {text}".lower()

            if any(re.search(p, combined, re.IGNORECASE) for p in self.discovery_patterns):
                # Found a match! Build ReservationOption accordingly
                is_link = bool(href)
                return ReservationOption(
                    provider=self.provider_type,
                    href=href if is_link else None,
                    selector=None,
                    is_link=is_link,
                    is_button=False,
                )
        return None

    def month_to_number(self, month_name: str) -> int:
        """Convert month name to number for comparison"""
        months = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        return months.get(month_name, 0)
    
    @abstractmethod
    async def select_reservation_party_size(self, page, party_size: int) -> ActionResult:
        """Select party size for the reservation."""
        pass
    
    @abstractmethod
    async def select_reservation_date(self, page, date: str) -> ActionResult:
        """Select date for the reservation."""
        pass
    
    @abstractmethod
    async def select_reservation_time(self, page, desired_time: str) -> ActionResult:
        """Select time for the reservation."""
        pass
    
    @abstractmethod
    async def select_from_available_time_slots(self, page, desired_time: str) -> ActionResult:
        """Select time from available time slots."""
        pass
    
    @abstractmethod
    async def update_reservation_contact_info(self, page, first_name: str, last_name: str, 
                                            phone: str, email: str) -> ActionResult:
        """Update contact information for the reservation."""
        pass
    
    
    @abstractmethod
    async def reserve_with_provider(self, page, party_size: int, date: str, time_24h: str,
                                  first_name: str, last_name: str, phone: str, email: str) -> ActionResult:
        """
        Complete reservation flow for this provider.
        This is the main method that orchestrates the entire reservation process.
        """
        pass
    
    @abstractmethod
    async def finalize_booking(self, page) -> ActionResult:
        """
        Provider-specific final booking steps.
        This should handle clicking the final book button and confirming the reservation.
        """
        pass
    
    def get_reservation_errors(self) -> dict:
        """Get provider-specific error messages."""
        return RESERVATION_ERRORS 