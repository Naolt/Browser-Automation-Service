from typing import Optional
from browser_use import ActionResult, BrowserSession
# from services.actions import controller
from services.actions.utils import build_reservation_failure_message, parse_date, round_up_to_next_half_hour, to_time_string, RESERVATION_ERRORS
from datetime import datetime
import re
from datetime import datetime, timedelta
from browser_use import Controller

controller = Controller()


NEXT_AVAILABLE_DATES_SELECTOR = 'text=Next available dates'
TIME_SLOT_BUTTON_SELECTOR = 'button[aria-disabled="false"]'


RESERVATION_URL_PREFIX = "https://www.google.com/maps/reserve"


def is_valid_url(url:str):
    RESERVATION_URL_PREFIX = "https://www.google.com/maps/reserve"

    return url.startswith(RESERVATION_URL_PREFIX)

#--------------------------------- 
#--------------------------------- 
# Reseve with google tools


@controller.action(
    'Select a reservation time (24-hour format HH:MM, e.g., "13:30") and confirm if the time is available.'
)
async def select_reservation_time(page, desired_time: str) -> ActionResult:
    print(f"[select_reservation_time_flex] Requested: {desired_time}")

    try:

        if not page or not is_valid_url(page.url):
            print("[select_reservation_party_size] ❌ Wrong page, please make sure it's google reservation page with prefix like:{RESERVATION_URL_PREFIX}")
            return ActionResult(extracted_content=f"❌ Wrong page, please make sure it's google reservation page with prefix like:{RESERVATION_URL_PREFIX}")
        
        if not page:
            return ActionResult(extracted_content="❌ Could not find the reservation tab.")
        
        # Close popups if any
        await close_popup_by_selector(page=page, selector='[aria-label="Close"]')

        # Step 1: Parse user-requested time
        requested_dt = datetime.strptime(desired_time, "%H:%M")
        dropdown_time_dt = round_up_to_next_half_hour(requested_dt)
        dropdown_time_str = to_time_string(dropdown_time_dt)

        print(f"[select_reservation_time_flex] Dropdown base: {dropdown_time_str}")

        # Step 2: Open the time dropdown selector
        dropdown_trigger = page.locator('div[role="combobox"]').nth(1)
        await dropdown_trigger.click()

        # Step 3: Try selecting the dropdown option matching closest 30-min interval
        dropdown_option = page.locator(f'li[data-value="{dropdown_time_str}"]')
        if await dropdown_option.count() == 0:
            message = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
            print(f"[select_reservation_time_flex] ❌ Time option not in dropdown: {dropdown_time_str}")
            return ActionResult(extracted_content=message)

        # Click only the first matched element
        first_option = dropdown_option.first
        await first_option.scroll_into_view_if_needed()
        await first_option.click()
        
        # Wait for visible time slot buttons to appear instead of fixed sleep
        await page.wait_for_selector('button:has-text(":")', timeout=10000)

        # Step 4: Check for fallback panel (means no slots around this)
        if await page.locator(NEXT_AVAILABLE_DATES_SELECTOR).count() > 0:
            message = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
            print("[select_reservation_time_flex] ❌ 'Next available dates' panel detected")
            return ActionResult(extracted_content=message)

        # Step 5: # Get visible time slot buttons
        all_buttons = await page.locator('button:has-text(":")').all()
        valid_time_buttons = []

        print(f"[select_reservation_time_flex] Found {len(all_buttons)} time buttons.")
        
        for button in all_buttons:
            print(f"[select_reservation_time_flex] Checking button: {await button.inner_text()} out of {len(all_buttons)}")
            text = (await button.inner_text()).strip()
            if re.match(r'^\d{1,2}:\d{2}$', text):
                if not await button.is_disabled():
                    data_slot = await button.get_attribute("data-slot")
                    is_redirect = data_slot and "http" in data_slot

                    if is_redirect:
                        print(f"[select_reservation_time_flex] ⚠️ Skipping redirect-style button: {text}")
                        continue
                    
                    valid_time_buttons.append((text, button))

        # Print the valid time buttons for debugging
        print(f"[select_reservation_time_flex] Found {len(valid_time_buttons)} valid time buttons:")
        for time_str, btn in valid_time_buttons:
            print(f"  - {time_str} (disabled: {await btn.is_disabled()})")

        # Step 6: Find the closest available button
        closest_button = None
        min_diff = timedelta(minutes=9999)


        # Define allowed time window
        earliest_time = requested_dt - timedelta(minutes=15)
        latest_time = requested_dt + timedelta(minutes=30)


        # Cap latest_time at 23:59 to avoid next-day wrap
        if latest_time.day > requested_dt.day:
            latest_time = requested_dt.replace(hour=23, minute=59, second=0, microsecond=0)

        for time_str, button in valid_time_buttons:
            try:
                btn_time_only = datetime.strptime(time_str, "%H:%M").time()
                btn_time = requested_dt.replace(hour=btn_time_only.hour, minute=btn_time_only.minute)

                if not (earliest_time <= btn_time <= latest_time):
                    continue

                diff = abs((btn_time - requested_dt).total_seconds())
                if diff < min_diff.total_seconds():
                    min_diff = timedelta(seconds=diff)
                    closest_button = (time_str, button)

            except ValueError:
                continue  # Skip if somehow invalid format

        # Step 7: Click the closest available button
        if closest_button:
            print(f"[select_reservation_time_flex] ✅ Closest time found: {closest_button[0]}")
            await closest_button[1].scroll_into_view_if_needed()
            await page.wait_for_timeout(200)  # 200ms pause before clicking
            await closest_button[1].click()
            return ActionResult(extracted_content=f"✅ Closest time with in allowed range selected Successfully. Here is the time: {closest_button[0]}")
        else:
            message = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
            print(f"[select_reservation_time_flex] ❌ Booking Can't proceed, No available time near {desired_time}")
            return ActionResult(extracted_content=message)

    except Exception as e:
        print(f"[select_reservation_time_flex] ❌ Error: {str(e)}")
        return ActionResult(extracted_content=f"❌ Error selecting time: {str(e)}")

@controller.action(
    'Select a reservation party size (number) and confirm if the party size is available.'
)
async def select_reservation_party_size(page, party_size: int ) -> ActionResult:
    print(f"[select_party_size] Trying to select party size: {party_size}")
    try:
        if not page or not is_valid_url(page.url):
            print("[select_reservation_party_size] ❌ Wrong page, please make sure it's google reservation page with prefix like:{RESERVATION_URL_PREFIX}")
            return ActionResult(extracted_content=f"❌ Wrong page, please make sure it's google reservation page with prefix like:{RESERVATION_URL_PREFIX}")
        
        if not page:
            return ActionResult(extracted_content="❌ Could not find the reservation tab.")
        
        # Close popups if any
        await close_popup_by_selector(page=page, selector='[aria-label="Close"]')

        # Locate dropdown trigger – assuming it's the first combobox
        dropdown_trigger = page.locator('div[role="combobox"]').nth(0)
        await dropdown_trigger.click()
        await page.wait_for_timeout(300)

        # Find the desired option
        option = page.locator(f'li[data-value="{party_size}"]')

        if await option.count() == 0:
            message = build_reservation_failure_message(RESERVATION_ERRORS["party_size_not_available"])
            print(f"[select_party_size] ❌ Could not find party size option: {party_size}")
            return ActionResult(extracted_content=message)

        # Scroll into view and click
        await option.scroll_into_view_if_needed()
        print(f"[select_party_size] Clicking on party size {party_size}")
        await option.click()
        await page.wait_for_timeout(400)

        # Confirm selection
        selected_option = await option.get_attribute("aria-selected")
        if selected_option == "true":
            print(f"[select_party_size] ✅ Party size {party_size} selected successfully.")
            return ActionResult(extracted_content=f"✅ Party size {party_size} selected.")
        else:
            print(f"[select_party_size] ⚠️ Selection attempted but not confirmed via aria-selected.")
            return ActionResult(extracted_content=f"⚠️ Tried selecting party size {party_size}, but not confirmed.")

    except Exception as e:
        print(f"[select_party_size] ❌ Error selecting party size: {str(e)}")
        return ActionResult(extracted_content=f"❌ Error selecting party size: {str(e)}")


@controller.action(
    'Select a reservation date (YYYY-MM-DD) and confirm if the date is available.'
)
async def select_reservation_date(page, date: str) -> ActionResult:
    print(f"[select_reservation_date] Starting date selection for: {date}")
    try:
        if not page or not is_valid_url(page.url):
            print(f"[select_reservation_date] ❌ Wrong page, please make sure it's google reservation page with prefix like:{RESERVATION_URL_PREFIX}")
            return ActionResult(extracted_content=f"❌ Wrong page, please make sure it's google reservation page with prefix like:{RESERVATION_URL_PREFIX}")
        
        if not page:
            return ActionResult(extracted_content="❌ Could not find the reservation tab.")
        
        # Close popups if any
        await close_popup_by_selector(page=page, selector='[aria-label="Close"]')

        target_dt = parse_date(date)
        target_month = target_dt.strftime("%B")  # e.g., "June"
        target_year = target_dt.year
        print(f"[select_reservation_date] Target: {target_month} {target_year}")

        # Step 1: Open the calendar widget
        calendar_input = page.locator('[aria-label="Select reservation date"] [role="button"]')
        await calendar_input.click()
        print("[select_reservation_date] Clicked calendar input")

        # Wait until calendar widget is open
        try:
            await page.wait_for_selector('[aria-label][aria-disabled="false"]', timeout=3000)
            print("[select_reservation_date] Calendar widget opened")
        except Exception:
            return ActionResult(extracted_content="❌ Calendar widget did not open.")
        
        await page.wait_for_timeout(300)

        # Get Next and Previous buttons
        next_button = page.locator('[aria-label="next month"][role="button"]')
        prev_button = page.locator('[aria-label="previous month"][role="button"]')

        # Get current calendar header
        current_month_label = prev_button.locator("xpath=../following-sibling::*[1]")

        for _ in range(12):  # Prevent infinite loop
            label_text = (await current_month_label.inner_text()).strip()
            print(f"[select_reservation_date] Current calendar label: {label_text}")
            try:
                current_month, current_year = label_text.split()
                current_year = int(current_year)
            except ValueError:
                return ActionResult(
                    extracted_content=f"❌ Unexpected calendar header format: '{label_text}'"
                )

            if current_month == target_month and current_year == target_year:
                print(f"[select_reservation_date] Navigated to correct month: {current_month} {current_year}")
                break

            await next_button.click()
            print("[select_reservation_date] Clicked next month")
            await page.wait_for_timeout(400)
        else:
            return ActionResult(
                extracted_content=f"❌ Could not navigate to {target_month} {target_year} in calendar."
            )

        # Step 5: Try to select the requested date
        day = target_dt.day
        month_short = target_dt.strftime("%b")  # "Jun"
        weekday = target_dt.strftime("%A")      # "Thursday"
        target_aria_label = f"{weekday} {day} {month_short}"
        print(f"[select_reservation_date] Looking for aria-label: {target_aria_label}")

        available_dates = page.locator('[aria-label][aria-disabled="false"]')
        date_elements = await available_dates.all()

        for el in date_elements:
            label = await el.get_attribute("aria-label")
            if label == target_aria_label:
                print(f"[select_reservation_date] Found and clicking date: {label}")
                await el.click()
                await page.wait_for_timeout(500)
                return ActionResult(extracted_content=f"✅ Date {date} selected")

        # If not found, log all available dates
        available_labels = [await el.get_attribute("aria-label") for el in date_elements]
        if len(available_labels) <= 2:
            available_labels = []
        available_labels = available_labels[2:] 

        message = build_reservation_failure_message(RESERVATION_ERRORS["date_not_available"])

        print(message)
        return ActionResult(extracted_content=message)
    
    except Exception as e:
        print(f"[select_reservation_date] ❌ Exception occurred: {str(e)}")
        return ActionResult(extracted_content=f"❌ Error selecting date: {str(e)}")


@controller.action("Update reservation contact information if possible.")
async def update_reservation_contact_info(
    page,
    first_name: str = "Naol",
    last_name: str = "Delesa",
    phone: str = "+251 91 234 5678",
    email: str = "naol.delesa@example.com",
) -> ActionResult:
    try:
        await page.wait_for_timeout(3000)
        # await page.screenshot(path="images/contact_info.png")
        print("[update_contact_info] Looking for Edit Contact Info button...")
        edit_button = page.locator('[aria-label="Edit contact info"]')

        if await edit_button.count() > 0 and not await edit_button.is_disabled():
            print("[update_contact_info] Clicking Edit Contact Info...")
            await edit_button.click()
            await page.wait_for_timeout(2000)
            # await page.screenshot(path="after_click.png")

            print("[update_contact_info] Filling contact fields...")
            await page.locator('[aria-label="First name"]').fill(first_name)
            await page.locator('[aria-label="Surname"]').fill(last_name)
            await page.locator('[aria-label="Telephone number"]').fill(phone)
            await page.locator('[aria-label="Email"]').fill(email)
            await page.wait_for_timeout(400)

            update_button = page.locator('button:has-text("Update info")')
            if await update_button.count() > 0 and not await update_button.is_disabled():
                print("[update_contact_info] Clicking Update Info button...")
                await update_button.click()
                await page.wait_for_timeout(500)
                return ActionResult(extracted_content="✅ Contact info updated.")
            else:
                print("[update_contact_info] ⚠️ Update Info button not found or disabled.")
                return ActionResult(extracted_content="⚠️ Contact info form filled but update button was disabled.")
        else:
            print("[update_contact_info] ℹ️ Edit Contact Info not available.")
            return ActionResult(extracted_content="ℹ️ Edit contact info section not found or disabled.")
    except Exception as e:
        print(f"[update_contact_info] ⚠️ Optional contact update failed: {e}")
        return ActionResult(extracted_content=f"⚠️ Contact info update skipped due to error: {str(e)}")
 

@controller.action("Click the first provider option (e.g., Zomato or EazyDiner) in a 'Continue with' popup if it appears.")
async def select_reservation_provider(page) -> ActionResult:
    """
    Looks for the 'Continue with' provider popup and clicks the first available option.
    If the popup is not found, it does nothing.
    """
    try:
        await page.wait_for_selector('text="Continue with"', timeout=3000)
    except Exception:
        return ActionResult(extracted_content="ℹ️ No 'Continue with' popup found — skipping.")

    try:
        # Find all headings on the page
        headings = await page.locator('[role="heading"]').all()
        for heading in headings:
            text = (await heading.inner_text()).strip()
            if text == "Continue with":
                print("[handle_provider_popup] ✅ 'Continue with' popup found.")
                
                # Go from heading to its parent element
                parent = heading.locator('xpath=..')

                # print("[handle_provider_popup] Parent element found,",await parent.inner_html())

                # Then go to the parent's next sibling element
                next_sibling = parent.locator('xpath=following-sibling::*[1]')

                # print("[handle_provider_popup] Next sibling element found,",await next_sibling.inner_html())

                # From that sibling, get all buttons
                buttons = next_sibling.locator('[role="button"]:not([aria-disabled="true"])')

                # Loop through them and find the first visible one
                count = await buttons.count()

                print(f"[handle_provider_popup] Found {count} provider buttons in the popup.")

                
                for i in range(count):
                    btn = buttons.nth(i)
                    try:
                        await btn.wait_for(state="visible", timeout=2000)
                        await btn.scroll_into_view_if_needed()
                        if await btn.is_enabled():
                            print("[handle_provider_popup] First enabled provider button HTML:\n", await btn.inner_html())
                            await page.wait_for_timeout(200)  # 200ms pause before clicking
                            await btn.click()
                            return ActionResult(extracted_content="✅ Clicked the first enabled provider option.")
                        else:
                            print(f"[handle_provider_popup] Button at index {i} is not enabled.")
                    except Exception as e:
                        print(f"[handle_provider_popup] Skipped button at index {i}, not interactable: {e}")

                print("[handle_provider_popup] ❌ 'Continue with' popup found, but no clickable option.")
                return ActionResult(extracted_content="❌ 'Continue with' popup found, but no clickable option.")
            


        # If we go through all headings and find nothing
        print("[handle_provider_popup] ℹ️ No 'Continue with' popup found — skipping.")
        return ActionResult(extracted_content="ℹ️ No 'Continue with' popup found — skipping.")

    except Exception as e:
        print(f"[handle_provider_popup] ❌ Exception while handling popup: {str(e)}")
        return ActionResult(extracted_content=f"⚠️ Exception while handling popup: {str(e)}")


async def interact_with_error_modal(page):

    try:
        # Wait for the modal to appear
        await page.wait_for_selector('[role="alertdialog"]', timeout=5000)
    
        modal_locator = page.locator('[role="alertdialog"]')

        # Ensure the modal is visible before attempting to interact with it
        await modal_locator.wait_for(state="visible")

        # Find all buttons within the first modal (assuming there might be multiple)
        buttons = modal_locator.locator('[role="button"]')

        count = await buttons.count()
        if count == 0:
            print("[interact_with_error_modal] ❌ No buttons found in the error modal.")
            return ActionResult(extracted_content="❌ No buttons found in the error modal.")
        else:
            for i in range(count):
                button = buttons.nth(i)
                try:
                    await button.wait_for(state="visible", timeout=1000)
                    await button.scroll_into_view_if_needed()
                    print(f"[interact_with_error_modal] Clicking visible button at index {i}")
                    await button.click()
                    return ActionResult(extracted_content=f"✅ Clicked button at index {i} in error modal.")
                except:
                    print(f"[interact_with_error_modal] Skipped button at index {i}, not visible.")


        # You might want to add a wait here to see the effect or
        # wait for the modal to disappear.
        await modal_locator.wait_for(state="detached") # waits for it to disappear
        print("[interact_with_error_modal] Successfully interacted with the error modal.")
        return ActionResult(extracted_content="✅ Successfully interacted with the error modal.")
    except Exception as e:
        print(f"[interact_with_error_modal] ❌ Error while interacting with error modal: {str(e)}")
        return ActionResult(extracted_content=f"❌ Error while interacting with error modal: {str(e)}")



#--------------------------------- 
#--------------------------------- 


@controller.action('Prepare browser tabs for reservation by focusing on the reservation tab and closing others.')
async def focus_on_reservation_tab(browser_session: BrowserSession) -> ActionResult:
    
    ALLOWED_URL_PREFIXES = [
    "https://www.google.com/maps/reserve",
    ]
    print("[prepare_tabs_for_reservation] Cleaning up browser tabs...")

    if not browser_session.browser_context:
        print("[prepare_tabs_for_reservation] ❌ No browser context found.")
        return ActionResult(extracted_content="❌ No browser context found.")

    try:

        target_tab = None
        pages = browser_session.browser_context.pages

        for page in pages:
            url = page.url
            print(f"[prepare_tabs_for_reservation] Checking tab: {url}")
            if url.startswith(RESERVATION_URL_PREFIX):
                target_tab = page
            elif not any(url.startswith(prefix) for prefix in ALLOWED_URL_PREFIXES):
                print(f"[prepare_tabs_for_reservation] ❌ Closing disallowed tab: {url}")
                await page.close()

        if target_tab:
            await target_tab.bring_to_front()
            print(f"[prepare_tabs_for_reservation] ✅ Brought reservation tab to front: {target_tab.url}")
            return ActionResult(
                extracted_content=f"✅ Reservation tab found and focused: {target_tab.url}"
            )
        else:
            print("[prepare_tabs_for_reservation] ❌ No reservation tab found, please open a valid reservation page.")
            return ActionResult(
                extracted_content="❌ No reservation tab found, please open a valid reservation page."
            )
    except Exception as e:  
        print(f"[prepare_tabs_for_reservation] ❌ Error while preparing tabs: {str(e)}")
        return ActionResult(
            extracted_content=f"❌ Error while preparing tabs: {str(e)}"
        )



@controller.action("Click a close button in a popup if it exists.")
async def close_popup_by_selector(page, selector: Optional[str] = None) -> ActionResult:
    """
    Attempts to close a popup by clicking a button or element matching the provided selector.
    If no selector is provided, uses a default known selector.
    """
    DEFAULT_CLOSE_SELECTOR = '[aria-label="Close"]'  # You can change this based on your UI

    try:
        target_selector = selector or DEFAULT_CLOSE_SELECTOR
        close_button = page.locator(target_selector)

        count = await close_button.count()

        
        for i in range(count):
            button = close_button.nth(i)
            try:
                await button.wait_for(state="visible", timeout=1000)
                await button.scroll_into_view_if_needed()
                print(f"[close_popup_by_selector] Clicking visible button at index {i}")
                await button.click()
                return ActionResult(extracted_content=f"✅ Clicked button at index {i} in popup.")
            except:
                print(f"[close_popup_by_selector] Skipped button at index {i}, not visible.")

        print(f"[close_popup_by_selector] ❌ No popup close button found for selector: {target_selector}")
        return ActionResult(extracted_content=f"⚠️ No popup found with selector: {target_selector}")
    
    except Exception as e:
        print(f"[close_popup_by_selector] ❌ Error while closing popup: {str(e)}")
        return ActionResult(extracted_content=f"❌ Error while closing popup: {str(e)}")


@controller.action('Get list of available dates for a specific selected month on opened googles calendar widget.')
async def get_available_dates(page) -> ActionResult:

    print("[Called get_available_dates Action]")
    try:
        async def find_available_dates():
            elements = await page.locator('[aria-label][aria-disabled="false"]').all()
            if len(elements) <= 2:
                return []
            return elements[2:]  # Skip Prev and Next buttons

        # First attempt: current month
        date_elements = await find_available_dates()
        if date_elements:
            labels = [await el.get_attribute('aria-label') for el in date_elements]
            labels = [label for label in labels if label]
            print("[Called get_available_dates Action] Result", labels)
            return ActionResult(extracted_content=f"✅ Available dates this month: {', '.join(labels)}")

        return ActionResult(extracted_content="❌ No available dates")

    except Exception as e:
        return ActionResult(extracted_content=f"❌ Error retrieving dates: {str(e)}")


@controller.action('Clicks element. If the element is disabled it will respond that it is not available')
async def click_element(css_selector: str, page) -> ActionResult:
    # css_selector is an action param the LLM must provide when calling
    # page is a special framework-provided param to access the browser APIs (see below)
    if not css_selector:
        return ActionResult(extracted_content="❌ Error: CSS selector is required")
    element = page.locator(css_selector).first
    if not await element.count():
        return ActionResult(extracted_content=f"❌ Error: Could not find element with selector: {css_selector}")
    element = page.locator(css_selector)

    disabled = await element.get_attribute("aria-disabled")
    if disabled and disabled.lower() == "true":
        return ActionResult(extracted_content=f"❌ This element {css_selector} is not clickable, which means it's likely unavailable")
    await element.click()

    return ActionResult(extracted_content=f"Clicked element {css_selector}")

