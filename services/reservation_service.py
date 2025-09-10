from browser_use import ActionResult
from services.reservation_discovery_service import ReservationDiscoveryService
from services.actions.utils import build_reservation_failure_message, RESERVATION_ERRORS
from services.actions.provider.base_provider import BaseReservationProvider
import logging
logging.basicConfig(level=logging.INFO, filename="reservation_service.log")
logger = logging.getLogger(__name__)


class ReservationService:
    def __init__(self, providers: list[BaseReservationProvider]):
        self.discovery_service = ReservationDiscoveryService(providers)

    def log_message(self, message: str):
        logger.info(f"[ReservationService] {message}")

    async def try_click_find_table_button(self,page) -> None:
        try:
            button = page.locator('button:has-text("Find a table")')
            if await button.count() > 0:
                self.log_message("Clicking 'Find a table' to reveal reservation options...")
                await button.first.click()
                await page.wait_for_timeout(2000)
        except Exception as e:
            self.log_message(f"failed while trying to click find table button {e}")



    async def make_reservation(
        self, page, party_size: int, date: str, time_24h: str,
        first_name: str, last_name: str, phone: str, email: str,
    ) -> ActionResult:
        restaurant_name = "Restaurant"

        try:
            self.log_message(f"Starting reservation for {restaurant_name}")

            # Step 0: Check URL
            if "google.com/maps/place/" not in page.url:
                msg = "❌ Please open a Google Maps restaurant page before making a reservation."
                self.log_message(msg)
                return ActionResult(extracted_content=msg)

            # Step 1: Click 'Find a table' if available to reveal reservations
            await self.try_click_find_table_button(page)

            options = await self.discovery_service.discover_all_options(page)
            if not options:
                msg = build_reservation_failure_message(RESERVATION_ERRORS["reservation_system_not_available"])
                self.log_message(f"No options found: {msg}")
                return ActionResult(extracted_content=msg)

            recommended_option = self.discovery_service.select_best_option(options)
            if not recommended_option:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["reservation_system_not_available"])
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            provider_name = recommended_option.provider.value
            self.log_message(f"Selected option: Provider={provider_name}, href={recommended_option.href}")

            if recommended_option.href:
                await page.goto(recommended_option.href)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(3000)

                provider = next(
                    (p for p in self.discovery_service.providers if p.provider_type == recommended_option.provider),
                    None
                )

                if provider:
                    return await provider.reserve_with_provider(
                        page, party_size, date, time_24h, first_name, last_name, phone, email
                    )

                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["reservation_system_not_available"])
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            error_msg = build_reservation_failure_message(RESERVATION_ERRORS["reservation_system_not_available"])
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)    

        except Exception as e:
            err = f"❌ Error in smart reservation: {str(e)}"
            self.log_message(err)
            return ActionResult(extracted_content=err)
