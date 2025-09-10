from datetime import datetime
import re
from typing import Optional
from datetime import timedelta
from browser_use import ActionResult
from models.reservation_models import ProviderType
from services.actions.provider.base_provider import BaseReservationProvider
from services.actions.utils import RESERVATION_ERRORS, RESERVATION_SUCCESSES, build_reservation_failure_message, build_reservation_success_message, parse_date,round_up_to_next_half_hour, to_time_string
from playwright.async_api import expect

class GoogleProvider(BaseReservationProvider):
    """
    Google provider
    """
    
    def __init__(self):
        discovery_patterns = [
            r"https:\/\/www\.google\.(com|[a-z]{2,3})\/maps\/reserve(?:\/[a-zA-Z0-9_-]+)?(?:\?.*)?"
        ]
        super().__init__(provider_name="google", url_prefixes=["https://www.google.com/maps/reserve"], provider_type=ProviderType.GOOGLE, discovery_patterns=discovery_patterns)
        
    async def select_reservation_party_size(self, page, party_size: int) -> ActionResult:
        self.log_message(f"Trying to select party size: {party_size}")
        
        try:
            if not page or not self.is_valid_url(page.url):
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["wrong_page"].format(self.url_prefixes))
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
            
            # Close popups if any
            await self.close_popup_by_selector(page=page, selector='[aria-label="Close"]')

            # Locate dropdown trigger – assuming it's the first combobox
            dropdown_trigger = page.locator('div[role="combobox"]').nth(0)
            await dropdown_trigger.click()
            await page.wait_for_timeout(300)

            # Find the desired option
            option = page.locator(f'li[data-value="{party_size}"]')

            if await option.count() == 0:
                error_msg = f"❌ Could not find party size option: {party_size}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=build_reservation_failure_message(RESERVATION_ERRORS["party_size_not_available"]), success=False, error=error_msg)

            # Scroll into view and click
            await option.scroll_into_view_if_needed()
            self.log_message(f"Clicking on party size {party_size}")
            await option.click()
            await page.wait_for_timeout(400)

            # Confirm selection
            selected_option = await option.get_attribute("aria-selected")
            if selected_option == "true":
                self.log_message(f"✅ Party size {party_size} selected successfully.")
                return ActionResult(extracted_content=f"✅ Party size {party_size} selected.")
            else:
                error_msg = f"⚠️ Tried selecting party size {party_size}, but not confirmed."
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

        except Exception as e:
            error_msg = f"❌ Error selecting party size: {str(e)}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

    async def select_reservation_date(self, page, date: str) -> ActionResult:
        self.log_message(f"Starting date selection for: {date}")
        try:
            if not page or not self.is_valid_url(page.url):
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["wrong_page"].format(self.url_prefixes))
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
        
            # Close popups if any
            await self.close_popup_by_selector(page=page, selector='[aria-label="Close"]')

            target_dt = parse_date(date)
            target_month = target_dt.strftime("%B")  # e.g., "June"
            target_year = target_dt.year
            self.log_message(f"Target: {target_month} {target_year}")

            # Step 1: Open the calendar widget
            calendar_input = page.locator('[aria-label="Select reservation date"] [role="button"]')
            await calendar_input.click()
            self.log_message("Clicked calendar input")
            await page.wait_for_timeout(1000)

            # Wait until calendar widget is open
            try:
                await page.wait_for_selector('[aria-label][aria-disabled="false"]', timeout=3000)
                self.log_message("Calendar widget opened")
            except Exception:
                error_msg = build_reservation_failure_message(f"❌ Calendar widget did not open.")
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
            

            # Get Next and Previous buttons
            next_button = page.locator('[aria-label="next month"][role="button"]')
            prev_button = page.locator('[aria-label="previous month"][role="button"]')

            # Get current calendar header
            current_month_label = prev_button.locator("xpath=../following-sibling::*[1]")

            for _ in range(12):  # Prevent infinite loop
                label_text = (await current_month_label.inner_text()).strip()
                self.log_message(f"Current calendar label: {label_text}")
                try:
                    current_month, current_year = label_text.split()
                    current_year = int(current_year)
                except ValueError:
                    error_msg = f"❌ Unexpected calendar header format: '{label_text}'"
                    self.log_message(error_msg)
                    return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

                if current_month == target_month and current_year == target_year:
                    self.log_message(f"Navigated to correct month: {current_month} {current_year}")
                    break

                await next_button.click()
                self.log_message("Clicked next month")
                await page.wait_for_timeout(1000)
            else:
                error_msg = f"❌ Could not navigate to {target_month} {target_year} in calendar."
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

            # Step 5: Try to select the requested date
            day = target_dt.day
            month_short = target_dt.strftime("%b")  # "Jun"
            weekday = target_dt.strftime("%A")      # "Thursday"
            target_aria_label = f"{weekday} {day} {month_short}"
            self.log_message(f"Looking for aria-label: {target_aria_label}")

            available_dates = page.locator('[aria-label][aria-disabled="false"]')
            date_elements = await available_dates.all()

            for el in date_elements:
                label = await el.get_attribute("aria-label")
                if label == target_aria_label:
                    self.log_message(f"Found and clicking date: {label}")
                    await el.click()
                    await page.wait_for_timeout(1000)
                    # Wait for visible time slot buttons to appear instead of fixed sleep
                    await page.wait_for_selector('button:has-text(":")', timeout=10000)
                    return ActionResult(extracted_content=f"✅ Date {date} selected")

            # If not found, log all available dates
            available_labels = [await el.get_attribute("aria-label") for el in date_elements]
            if len(available_labels) <= 2:
                available_labels = []
            available_labels = available_labels[2:] 

            error_msg = build_reservation_failure_message(RESERVATION_ERRORS["date_not_available"])
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
        
        except Exception as e:
            error_msg = f"❌ Error selecting date: {str(e)}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

    async def select_reservation_time(self, page, desired_time: str) -> ActionResult:
        self.log_message(f"Requested: {desired_time}")

        try:

            if not page or not self.is_valid_url(page.url):
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["wrong_page"].format(self.url_prefixes))
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
            
            if not page:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["reservation_tab_not_found"])
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
            
            # Close popups if any
            await self.close_popup_by_selector(page=page, selector='[aria-label="Close"]')

            # Step 1: Parse user-requested time
            requested_dt = datetime.strptime(desired_time, "%H:%M")
            dropdown_time_dt = round_up_to_next_half_hour(requested_dt)
            dropdown_time_str = to_time_string(dropdown_time_dt)

            self.log_message(f"Dropdown base: {dropdown_time_str}")

            # Step 2: Open the time dropdown selector
            dropdown_trigger = page.locator('div[role="combobox"]').nth(1)
            await dropdown_trigger.click()

            # Step 3: Try selecting the dropdown option matching closest 30-min interval
            dropdown_option = page.locator(f'li[data-value="{dropdown_time_str}"]')
            if await dropdown_option.count() == 0:
                message = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                self.log_message(f"❌ Time option not in dropdown: {dropdown_time_str}")
                return ActionResult(extracted_content=message, success=False, error=message)

            # Click only the first matched element
            first_option = dropdown_option.first
            await first_option.scroll_into_view_if_needed()
            await first_option.click()
            
            # Wait for visible time slot buttons to appear instead of fixed sleep
            await page.wait_for_selector('button:has-text(":")', timeout=10000)

            NEXT_AVAILABLE_DATES_SELECTOR = 'text=Next available dates' # TODO: This is a hardcoded selector, we need to find a better way to do this
            # Step 4: Check for fallback panel (means no slots around this)
            if await page.locator(NEXT_AVAILABLE_DATES_SELECTOR).count() > 0:
                message = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                self.log_message(f"❌ 'Next available dates' panel detected")
                return ActionResult(extracted_content=message, success=False, error=message)

            # Step 5: # Get visible time slot buttons
            all_buttons = await page.locator('button:has-text(":")').all()
            valid_time_buttons = []

            self.log_message(f"Found {len(all_buttons)} time buttons.")
            
            for button in all_buttons:
                self.log_message(f"Checking button: {await button.inner_text()} out of {len(all_buttons)}")
                text = (await button.inner_text()).strip()
                if re.match(r'^\d{1,2}:\d{2}$', text):
                    if not await button.is_disabled():
                        data_slot = await button.get_attribute("data-slot")
                        is_redirect = data_slot and "http" in data_slot

                        if is_redirect:
                            self.log_message(f"⚠️ Skipping redirect-style button: {text}")
                            continue
                        
                        valid_time_buttons.append((text, button))

            # Print the valid time buttons for debugging
            self.log_message(f"Found {len(valid_time_buttons)} valid time buttons:")
            for time_str, btn in valid_time_buttons:
                self.log_message(f"  - {time_str} (disabled: {await btn.is_disabled()})")

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
                self.log_message(f"✅ Closest time found: {closest_button[0]}")
                await closest_button[1].scroll_into_view_if_needed()
                await page.wait_for_timeout(200)  # 200ms pause before clicking
                await closest_button[1].click()
                await page.wait_for_timeout(200)
                success_msg = f"✅ Closest time with in allowed range selected Successfully. Here is the time: {closest_button[0]}"
                self.log_message(success_msg)
                return ActionResult(extracted_content=success_msg)
            else:
                message = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                self.log_message(f"❌ Booking Can't proceed, No available time near {desired_time}")
                return ActionResult(extracted_content=message, success=False, error=message)

        except Exception as e:
            error_msg = f"❌ Error selecting time: {str(e)}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

    async def select_from_available_time_slots(self, page, desired_time: str) -> ActionResult:
        return ActionResult(extracted_content=f"✅ Time {desired_time} selected")

    async def select_reservation_provider(self, page) -> ActionResult:
        
        try:
            if not page or not self.is_valid_url(page.url):
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["wrong_page"].format(self.url_prefixes))
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

            # Wait for the dialog to appear
            
            dialog = page.locator('div[role="dialog"]').first
            await dialog.wait_for(state="visible", timeout=10000)
            
            await page.wait_for_timeout(500)  # reduce wait time


            # Optional: give it time to settle (animations, etc.)
            await page.wait_for_timeout(3000)

            # Find valid provider buttons inside the dialog (not "Close")
            provider_buttons = dialog.locator('div[role="button"][aria-label^="Book with"]')

            if await provider_buttons.count() > 0:

                count = await provider_buttons.count()
                self.log_message(f"✅ Found {count} provider button(s) inside the dialog.")

                for i in range(count):
                    btn = provider_buttons.nth(i)

                    
                    try:
                        await btn.scroll_into_view_if_needed()
                        await btn.wait_for(state="visible", timeout=5000)
                        await btn.wait_for(state="attached", timeout=5000)

                        self.log_message(f"Before clicking provider button #{i}")
                        # await btn.screenshot(path=f"before_click_btn_{i}.png")

                        # Stabilize click: hover + small wait before clicking
                        await btn.hover()
                        await page.wait_for_timeout(1000)

                        self.log_message(f"Clicking provider button #{i}")
                        await btn.click()

                        # Wait a bit to see if modal closes prematurely
                        await page.wait_for_timeout(2000)

                        # Check if dialog is still there
                        if await btn.is_visible():
                            self.log_message("⚠️ Dialog still visible, might have failed")
                        else:
                            self.log_message("✅ Dialog disappeared – assuming click succeeded")
                            self.log_message(f"✅ Clicked provider button #{i}")
                            break

                    except Exception as e:
                        self.log_message(f"⚠️ Failed to click provider button #{i}: {e}")

            if not await self.book_modal_is_visible(page):
                error_msg = "❌ No clickable provider button found"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

            return ActionResult(extracted_content="✅ Successfully clicked provider.")

        except Exception as e:
            error_msg = f"❌ Error selecting provider: {str(e)}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

    async def update_reservation_contact_info(self, page, first_name: str, last_name: str, phone: str, email: str) -> ActionResult:
        try:
            if not page or not self.is_valid_url(page.url):
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["wrong_page"].format(self.url_prefixes))
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
            
            self.log_message("Looking for Edit Contact Info button...")

            # wait for the contact info to appear
            await page.wait_for_selector('[aria-label="Edit contact info"]', timeout=5000)
            await page.wait_for_timeout(2000)

            edit_button = page.locator('[aria-label="Edit contact info"]')

            if await edit_button.count() > 0 and not await edit_button.is_disabled():
                self.log_message("Clicking Edit Contact Info...")
                await edit_button.click()
                await page.wait_for_timeout(2000)
                # await page.screenshot(path="after_click.png")

                self.log_message("Filling contact fields...")
                await page.locator('[aria-label="First name"]').fill(first_name)
                await page.locator('[aria-label="Surname"]').fill(last_name)
                await page.locator('[aria-label="Telephone number"]').fill(phone)
                await page.locator('[aria-label="Email"]').fill(email)
                await page.wait_for_timeout(400)

                update_button = page.locator('button:has-text("Update info")')
                if await update_button.count() > 0 and not await update_button.is_disabled():
                    self.log_message("Clicking Update Info button...")
                    await update_button.click()
                    await page.wait_for_timeout(500)
                    return ActionResult(extracted_content="✅ Contact info updated.")
                else:
                    self.log_message("⚠️ Update Info button not found or disabled.")
                    return ActionResult(extracted_content="⚠️ Contact info form filled but update button was disabled.")
            else:
                self.log_message("ℹ️ Edit Contact Info not available.")
                return ActionResult(extracted_content="ℹ️ Edit contact info section not found or disabled.")
        except Exception as e:
            self.log_message(f"⚠️ Optional contact update failed: {e}")
            return ActionResult(extracted_content=f"⚠️ Contact info update skipped due to error: {str(e)}")
    
    async def close_popup_by_selector(self, page, selector: Optional[str] = None) -> ActionResult:
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
                    self.log_message(f"Clicking visible button at index {i}")
                    await button.click()
                    self.log_message("clicked close button")
                    return ActionResult(extracted_content=f"✅ Clicked button at index {i} in popup.")
                except:
                    self.log_message(f"Skipped button at index {i}, not visible.")

            error_msg = f"⚠️ No popup close button found for selector: {target_selector}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
        
        except Exception as e:
            error_msg = f"⚠️ Error while closing popup: {str(e)}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

    async def interact_with_error_modal(self, page) -> ActionResult:    
        self.log_message("[interact_with_error_modal] Interacting with error modal...")
        try:
            if not page or not self.is_valid_url(page.url):
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["wrong_page"].format(self.url_prefixes))
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
            
            # Wait for the modal to appear  
            await page.wait_for_selector('[role="alertdialog"]', timeout=5000)
        
            modal_locator = page.locator('[role="alertdialog"]')

            # Ensure the modal is visible before attempting to interact with it
            await modal_locator.wait_for(state="visible")

            # Find all buttons within the first modal (assuming there might be multiple)
            buttons = modal_locator.locator('[role="button"]')

            count = await buttons.count()
            if count == 0:
                self.log_message("[interact_with_error_modal] ❌ No buttons found in the error modal.")
                return ActionResult(extracted_content="❌ No buttons found in the error modal.", success=False, error="❌ No buttons found in the error modal.")
            else:
                for i in range(count):
                    button = buttons.nth(i)
                    try:
                        await button.wait_for(state="visible", timeout=1000)
                        await button.scroll_into_view_if_needed()
                        self.log_message(f"[interact_with_error_modal] Clicking visible button at index {i}")
                        await button.click()
                        return ActionResult(extracted_content=f"✅ Clicked button at index {i} in error modal.")
                    except:
                        self.log_message(f"[interact_with_error_modal] Skipped button at index {i}, not visible.")


            # You might want to add a wait here to see the effect or
            # wait for the modal to disappear.
            await modal_locator.wait_for(state="detached") # waits for it to disappear
            self.log_message("[interact_with_error_modal] Successfully interacted with the error modal.")
            return ActionResult(extracted_content="✅ Successfully interacted with the error modal.")
        except Exception as e:
            self.log_message(f"[interact_with_error_modal] ❌ Error while interacting with error modal: {str(e)}")
            return ActionResult(extracted_content=f"❌ Error while interacting with error modal: {str(e)}", success=False, error=f"❌ Error while interacting with error modal: {str(e)}")

    async def handle_error_modal(self, page) -> ActionResult:
        try:
            if not page or not self.is_valid_url(page.url):
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["wrong_page"].format(self.url_prefixes))
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
            
            error_modal = page.locator('text="Booking error"')
            if await error_modal.count() > 0:
                self.log_message("[handle_error_modal] ⚠️ Error modal detected, trying to interact with it...")
                await self.interact_with_error_modal(page)
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

            return ActionResult(extracted_content="✅ No error modal exists.")
        except Exception as e:
            self.log_message(f"[check_if_error_modal_exists] ❌ Error while checking if error modal exists: {str(e)}")
            return ActionResult(extracted_content=f"❌ Error while checking if error modal exists: {str(e)}", success=False, error=f"❌ Error while checking if error modal exists: {str(e)}")

    async def finalize_booking(self, page) -> ActionResult:
        try:
            if not page or not self.is_valid_url(page.url):
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["wrong_page"].format(self.url_prefixes))
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
            
            self.log_message("Looking for Book button...")

            await page.wait_for_selector('button:has-text("Book")', timeout=5000)

            book_button = page.locator('button:has-text("Book")')

            if await book_button.count() == 0:
                error_msg = "❌ Book button not found after Continue."
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

            if await book_button.is_disabled():
                error_msg = "❌ Book button is present but disabled."
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

            # Scroll into view before clicking
            self.log_message("Scrolling Book button into view...")
            await book_button.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)

            # Click the Book button 
            self.log_message("Clicking Book button...")
            await book_button.click()
            await page.wait_for_timeout(5000)


            # Wait for either success or error
            done_button = page.locator('button:has-text("Done")')
            error_text = page.locator('text="Booking error"')

            overall_timeout = 10000 # 10 seconds

            await expect(done_button.or_(error_text)).to_be_visible(timeout=overall_timeout)

            if await error_text.count() > 0:
                # Optionally capture the reason from the alert modal if available
                reason_text = await page.locator('[role="alertdialog"]').inner_text()

                await self.interact_with_error_modal(page)

                message = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                self.log_message(message)
                self.log_message(f"❌ Booking failed, Time slot not available: {reason_text}")
                return ActionResult(extracted_content=message, success=False, error=message)

            if await done_button.count() == 0:
                error_msg = "❌ Couldn't find booking confirmation button after booking."
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

            if await done_button.is_disabled():
                error_msg = "❌ Done button is present but disabled."
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

            # Scroll into view before clicking
            self.log_message("Scrolling Done button into view...")
            await done_button.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)

            # Click the Done button
            self.log_message("Clicking Done button...")
            await done_button.click()
            await page.wait_for_timeout(1000)

            success_msg = "✅ Reservation complete and booked."
            self.log_message(success_msg)
            return ActionResult(extracted_content=success_msg)

        except Exception as e:
            error_msg = f"❌ Error while finalizing booking: {str(e)}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

    async def reserve_with_provider(self, page, party_size: int, date: str, time_24h: str,
                                  first_name: str, last_name: str, phone: str, email: str) -> ActionResult:
        try:
            # Step 1: Check the sent page
            if not page or not self.is_valid_url(page.url):
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["wrong_page"].format(self.url_prefixes))
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg, success=False, error=error_msg)
    
            # Step 2: Close popups if any
            await self.close_popup_by_selector(page=page, selector='[aria-label="Close"]')

            # Step 3: Select party size
            party_size_result = await self.select_reservation_party_size(page=page, party_size=party_size)
            if not party_size_result.extracted_content.startswith("✅"):
                return party_size_result
            
            await page.wait_for_timeout(1000)


            # Step 4: Select date
            # let's try two times to select the date
            for i in range(2):
                self.log_message(f"Attempt {i+1} to select date")
                date_result = await self.select_reservation_date(page=page, date=date)
                if date_result.extracted_content.startswith("✅"):
                    break
                else:
                    await page.wait_for_timeout(1000)

            if not date_result.extracted_content.startswith("✅"):
                return date_result
            
            
            await page.wait_for_timeout(1000)


            for i in range(2):
                self.log_message(f"Attempt {i+1} to select time")
                # Step 5: Select time   
                time_result = await self.select_reservation_time(page=page, desired_time=time_24h)
                if not time_result.extracted_content.startswith("✅"):
                    await page.wait_for_timeout(1000)
                    continue

                # Step 5.5: Check if the error modal appears
                error_modal_result = await self.handle_error_modal(page=page)
                if not error_modal_result.extracted_content.startswith("✅"):
                    return error_modal_result

                # Step 6: Select provider
                provider_result = await self.select_reservation_provider(page=page)
                if  provider_result.extracted_content.startswith("✅"):
                    break
                else:
                    await page.wait_for_timeout(1000)

            # Step 6.5: Check if the error modal appears
                error_modal_result = await self.handle_error_modal(page=page)
                if not error_modal_result.extracted_content.startswith("✅"):
                    return error_modal_result

            # Step 7: Update contact info
            await self.update_reservation_contact_info(page=page, first_name=first_name, last_name=last_name, phone=phone, email=email)

            await page.wait_for_timeout(1000)

            # Step 8: Finalize booking
            finalize_booking_result = await self.finalize_booking(page=page)
            if not finalize_booking_result.extracted_content.startswith("✅"):
                return finalize_booking_result
            

            success_msg = build_reservation_success_message(RESERVATION_SUCCESSES["reservation_complete"].format(party_size=party_size, date=date, time_24h=time_24h))
            return ActionResult(extracted_content=success_msg, success=True, is_done=True)

        except Exception as e:
            error_msg = f"❌ Error while reserving with provider: {str(e)}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg, success=False, error=error_msg)

    async def book_modal_is_visible(self, page) -> bool:
        try:
            if not page or not self.is_valid_url(page.url):
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["wrong_page"].format(self.url_prefixes))
                self.log_message(error_msg)
                return False
            
            await page.wait_for_selector('button:has-text("Book")', timeout=5000)

            return True

        except Exception as e:
            error_msg = f"❌ Error while checking if book modal is visible: {str(e)}"
            self.log_message(error_msg)
            return False
