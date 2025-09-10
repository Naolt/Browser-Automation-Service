from browser_use import BrowserSession, ActionResult
from playwright.async_api import Page, expect
# from services.actions import controller
from services.actions.provider.google_actions import is_valid_url, close_popup_by_selector, select_reservation_party_size, select_reservation_date, select_reservation_time, select_reservation_provider, update_reservation_contact_info, interact_with_error_modal
from services.actions.provider.google_provider import GoogleProvider
from services.actions.provider.open_table_provider import OpenTableProvider
from services.actions.provider.seven_rooms_provider import SevenRoomsProvider
from services.actions.utils import PROVIDER_URL_PREFIXES, RESERVATION_ERRORS, build_reservation_failure_message
from services.actions.discovery_service import ReservationDiscoveryService, ReservationMethod, ProviderType
from services.reservation_service import ReservationService

from browser_use import Controller

controller = Controller()

RESERVATION_URL_PREFIX = "https://www.google.com/maps/reserve"


@controller.action('Reset Browser Tabs')
async def reset_browser_tabs(browser_session: BrowserSession) -> ActionResult:
    """
    Closes all existing tabs and opens a new blank tab.
    This is useful for starting with a clean browser state.
    """
    # Get all existing tabs
    if browser_session.browser_context is None:
        return ActionResult(extracted_content="❌ Error: No browser context found.")

    all_tabs = browser_session.browser_context.pages

    # Close all existing tabs except the first one
    for tab in all_tabs[1:]:
        await tab.close()

    # If there are any tabs left, navigate the first one to about:blank
    if all_tabs:
        await all_tabs[0].goto('about:blank')
    else:
        # If no tabs exist, create a new one
        await browser_session.browser_context.new_page()

    return ActionResult(
        extracted_content='Reset browser tabs: closed all tabs and opened a new blank tab'
    )


@controller.action("Make a reservation using the best available option on the google maps page.")
async def make_reservation_smart(page, restaurant_google_maps_url: str, party_size: int, date: str, time_24h: str,
                                 first_name: str, last_name: str, phone: str, email: str) -> ActionResult:
    
    print("--------------------------------")
    print(f"Making reservation for {restaurant_google_maps_url} with party size {party_size} on {date} at {time_24h} with contact details {first_name} {last_name} {phone} {email}")
    print("--------------------------------")
    
    if not page:
        return ActionResult(extracted_content="❌ Error: No page found.")

    await page.goto(restaurant_google_maps_url)

    await page.wait_for_load_state('domcontentloaded')


    service = ReservationService([
        SevenRoomsProvider(),
        OpenTableProvider(),
        GoogleProvider(),
        # Add more providers here
    ])
    return await service.make_reservation(page, party_size, date, time_24h, first_name, last_name, phone, email)


