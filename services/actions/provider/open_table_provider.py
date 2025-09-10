import re
from typing import Optional
from datetime import datetime, timedelta
from browser_use import ActionResult, BrowserSession
from models.reservation_models import ProviderType, ReservationMethod, ReservationOption
from services.actions.provider.base_provider import BaseReservationProvider
from services.actions.utils import RESERVATION_ERRORS, RESERVATION_SUCCESSES, build_reservation_failure_message, build_reservation_success_message, parse_date, parse_phone_number
import logging
logging.basicConfig(level=logging.INFO, filename="open_table_provider.log")
logger = logging.getLogger(__name__)

class OpenTableProvider(BaseReservationProvider):
    """
    OpenTable provider
    """
    
    def __init__(self):
        discovery_patterns = [
            r"opentable\.com",
            r"opentable\.ae",
            r"open\s*table"
    ]
        super().__init__(provider_name="open_table", url_prefixes=["https://www.opentable.com/","https://www.opentable.ae/"], provider_type=ProviderType.OPENTABLE, discovery_patterns=discovery_patterns)

    async def get_active_container(self, page):
        container_selector = '[data-testid="bookable-cta"]'

        containers = page.locator(container_selector)
        for i in range(await containers.count()):
            if await containers.nth(i).is_visible():
                return containers.nth(i)
        return None

    async def select_reservation_party_size(self, page, party_size: int) -> ActionResult:
                
        """
        Select reservation party size
        """


        try:
            # Selectors:
            # 1. Party size selector button:
            party_size_button_selector = 'select[data-test="party-size-picker"]'
            # 2. Party size option:
            party_size_option_selector = 'option'

            self.log_message(f"Selecting party size: {party_size}")
        
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefixes}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            # 0. The main container that contains the party size
            main_container = await self.get_active_container(page)

            if not main_container:
                error_msg = f"❌ Could not find party size field container"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            await main_container.scroll_into_view_if_needed()
            
            # 1. Click the party size selector button to open the dropdown
            # 1.1 The selector resolves to 2 elements: One of them will be visible. 
            party_size_buttons = main_container.locator(party_size_button_selector)
            party_size_button = None

            for i in range(await party_size_buttons.count()):
                if await party_size_buttons.nth(i).is_visible():
                    party_size_button = party_size_buttons.nth(i)
                    break

            # 1.2 If no button is visible, return an error
            if not party_size_button:
                error_msg = f"❌ Could not find party size selector button"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)


            await party_size_button.scroll_into_view_if_needed()
            await party_size_button.click()
            await page.wait_for_timeout(500)  # Wait for dropdown to open

            # 2. Look for the specific party size option
            party_size_option = None

            # Get all party size options
            all_party_options = party_size_button.locator(party_size_option_selector)

            for i in range(await all_party_options.count()):
                option = all_party_options.nth(i)
                value = await option.get_attribute("value") # value is the party size

                self.log_message(f"Checking option {i+1}: value='{value}'")

                if value == str(party_size):
                    party_size_option = option
                    self.log_message(f"Found matching party size option: {party_size}")
                    break

            if not party_size_option:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["party_size_not_available"])
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            print(f"Party size option text: {await party_size_option.inner_text()}")
            print(f"Party size option value: {await party_size_option.get_attribute('value')}")

            # 3. Click the party size option
            await party_size_button.select_option(str(party_size))
            await party_size_button.click() # click the button to close the dropdown

            # Check for 'party too large' error message after selecting party size
            too_large_selector = '[data-test="time-slots"] [data-test="icNegative"] + div span'

            # wait for the selector to be visible with within the specified seconds
            try:
                await main_container.locator(too_large_selector).wait_for(state='visible', timeout=3000)

                too_large_elements = main_container.locator(too_large_selector)
                # Extract the error message text if possible
                error_text = await too_large_elements.first.inner_text()
                error_msg = build_reservation_failure_message(
                    f"Party size is too large to book online. {error_text}"
                )
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)
            except Exception as e:
                self.log_message(f"No error message found: {str(e)} — Continuing with the flow")


            success_msg = build_reservation_success_message(RESERVATION_SUCCESSES['party_size_selected'])
            self.log_message(success_msg)
            return ActionResult(extracted_content=success_msg)
        except Exception as e:
            error_msg = f"❌ Error selecting party size: {e}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)
   
    async def select_reservation_date(self, page, date: str) -> ActionResult:
        """Select date for the reservation."""
        
        try:

            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefixes}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            # 0. The main container that contains the party size
            main_container = await self.get_active_container(page)

            if not main_container:
                error_msg = f"❌ Could not find party size field container"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            await main_container.scroll_into_view_if_needed()


            # 1. Click on date input
            date_picker_button_selector = '[data-test="day-picker"]'
            date_picker_button = main_container.locator(date_picker_button_selector)

            # If date picker isn't visible 
            if await date_picker_button.count() == 0:
                error_msg = f"❌ Could not find date picker selecting button"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            date_picker_button = date_picker_button.first

            await date_picker_button.scroll_into_view_if_needed()
            await date_picker_button.click()
            
            # Wait for calendar to open
            picker_popup_wrapper = None
            try:
                picker_popup_selector = "#restaurantProfileDtpDayPicker-wrapper"
                await main_container.locator(picker_popup_selector).wait_for(state='visible', timeout=3000)
                picker_popup_wrapper = main_container.locator(picker_popup_selector).first
            except Exception:
                error_msg = "❌ Calendar widget did not open"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)
            
            # date picker controls
            prev_button = picker_popup_wrapper.locator('[name="previous-month"]').first
            next_button = picker_popup_wrapper.locator('[name="next-month"]').first

            # Current month&year
            calendar_header = picker_popup_wrapper.locator('#react-day-picker-2').first

            # Target date
            target_dt = parse_date(date)
            target_month = target_dt.strftime("%B")  # e.g., "August"
            target_year = target_dt.year
            target_day = target_dt.day

            # Navigate to correct month and year
            for _ in range(12):  # Prevent infinite loop
                try:
                    header_text = await calendar_header.inner_text()
                    self.log_message(f"Current calendar header: {header_text}")
                    
                    # Parse header text (e.g., "August 2025")
                    current_month, current_year = header_text.strip().split()
                    current_year = int(current_year)
                    
                    if current_month == target_month and current_year == target_year:
                        self.log_message(f"Navigated to correct month: {current_month} {current_year}")
                        break
                    
                    # Navigate to target month
                    if (current_year < target_year) or (current_year == target_year and self.month_to_number(current_month) < self.month_to_number(target_month)):
                        await next_button.click()
                        self.log_message("Clicked next month")
                    else:
                        await prev_button.click()
                        self.log_message("Clicked previous month")
                    
                    await page.wait_for_timeout(400)
                    
                except Exception as e:
                    self.log_message(f"❌ Error selecting date: {str(e)}")
                    return ActionResult(extracted_content=f"❌ Error selecting date: {str(e)}")
            else:
                error_msg = f"❌ Could not navigate to {target_month} {target_year} in calendar"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            
            # Select the correct date
            date_elements = picker_popup_wrapper.locator('table button[name="day"]:not([disabled])')

            target_date_found = False
            for i in range(await date_elements.count()):
                date_element = date_elements.nth(i)
                element_text = await date_element.inner_text()
                aria_label = await date_element.get_attribute("aria-label") # e.g "Friday, August 1"

                self.log_message(f"Checking Day: {aria_label}")

                target_date_formatted = target_dt.strftime("%A, %B %d")

                if target_date_formatted == aria_label:
                    await date_element.scroll_into_view_if_needed()
                    await date_element.click()
                    await page.wait_for_timeout(500)
                    target_date_found = True
                    break
            
            if not target_date_found:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["date_not_available"])
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            success_msg = build_reservation_success_message(RESERVATION_SUCCESSES['date_selected'])
            self.log_message(success_msg)
            return ActionResult(extracted_content=success_msg)
                
        except Exception as e:
            error_msg = f"❌ Error selecting date: {e}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)
            
    async def select_reservation_time(self, page, desired_time: str) -> ActionResult:
        """Select time for the reservation."""
        
        try:
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefixes}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            # 0. The main container that contains the party size
            main_container = await self.get_active_container(page)

            if not main_container:
                error_msg = f"❌ Could not find time field container"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            await main_container.scroll_into_view_if_needed()

            # 1. Click on time input
            time_picker_button_selector = '[data-test="time-picker"]'
            time_picker_button = main_container.locator(time_picker_button_selector)

            if await time_picker_button.count() == 0:
                error_msg = f"❌ Could not find time picker selecting button"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)
            
            time_picker_button = time_picker_button.first

            await time_picker_button.scroll_into_view_if_needed()
            await time_picker_button.click()

            # 2. Check if the desired time is available in the time picker and select it
            time_options = time_picker_button.locator('option')

            if await time_options.count() == 0:
                error_msg = f"❌ Could not find time options"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)


            # 3. Round up the desired time to the next half hour
            from services.actions.utils import round_up_to_next_half_hour, to_time_string
            requested_dt = datetime.strptime(desired_time, "%H:%M")
            dropdown_time_dt = round_up_to_next_half_hour(requested_dt)
            dropdown_time_str = to_time_string(dropdown_time_dt)

            self.log_message(f"Desired time: {desired_time}, Dropdown base: {dropdown_time_str}")
            
            # 4. Get the time options that are available
            valid_time_buttons = []
            for i in range(await time_options.count()):
                time_option = time_options.nth(i)
                value = await time_option.get_attribute("value")
                if value:
                    valid_time_buttons.append((value,time_option))

            self.log_message(f"Valid time buttons: {len(valid_time_buttons)} out of {await time_options.count()}")

            # 5. Find the closest available time within allowed window
            closest_button = None
            min_diff = timedelta(minutes=9999)
            
            # Define allowed time window (15 minutes before to 30 minutes after)
            earliest_time = requested_dt - timedelta(minutes=30)
            latest_time = requested_dt + timedelta(minutes=60)

             # Cap latest_time at 23:59 to avoid next-day wrap
            if latest_time.day > requested_dt.day:
                latest_time = requested_dt.replace(hour=23, minute=59, second=0, microsecond=0)
            

            self.log_message(f"Earliest time: {earliest_time}, Latest time: {latest_time}")
            self.log_message(f"Valid time buttons: {valid_time_buttons}")
            self.log_message(f"Requested time: {requested_dt}")
            # Find the closest available time
            for time_str, button in valid_time_buttons:
                try:
                    btn_time_only = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S").time()
                    btn_time = requested_dt.replace(hour=btn_time_only.hour, minute=btn_time_only.minute)
                    
                    self.log_message(f"Checking button time: {btn_time}")

                    if not (earliest_time <= btn_time <= latest_time):
                        continue
                    
                    diff = abs((btn_time - requested_dt).total_seconds())
                    if diff < min_diff.total_seconds():
                        min_diff = timedelta(seconds=diff)
                        closest_button = (time_str, button)
                        
                except Exception as e:
                    self.log_message(f"Error parsing time: {e}")
                    continue  # Skip if somehow invalid format

            # 6. Click the closest available button
            if not closest_button:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            self.log_message(f"Closest button: {closest_button[0]}")
            await time_picker_button.select_option(closest_button[0])
            await page.wait_for_timeout(500)  # Wait for selection to register
            await time_picker_button.click()

            formatted_time = datetime.strptime(closest_button[0], "%Y-%m-%dT%H:%M:%S").strftime("%H:%M")
    
            success_msg = build_reservation_success_message(f"✅ Time {formatted_time} selected successfully")
            self.log_message(success_msg)
            return ActionResult(extracted_content=success_msg)

            
        except Exception as e:
            error_msg = f"❌ Error selecting time: {e}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)
       
    async def select_from_available_time_slots(self, page, desired_time: str) -> ActionResult:
        """Select time from available time slots."""
        try:
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefixes}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            main_container = await self.get_active_container(page)

            if not main_container:
                error_msg = f"❌ Could not find time field container"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)
            
            await main_container.scroll_into_view_if_needed()

            # 1. Get the available time slots
            time_slots_selector = '[data-test="time-slots"] div[role="button"]' # e.g. <div role="button">6:30 PM</div>
            time_slots = main_container.locator(time_slots_selector)


            if await time_slots.count() == 0:
                error_msg = f"❌ Could not find time slots"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)
            
            # 2. Convert all the times to datetime objects
            time_slots_times = []
            for i in range(await time_slots.count()):
                time_slot = time_slots.nth(i)
                time_slot_text = await time_slot.inner_text()
                time_slots_times.append((datetime.strptime(time_slot_text, "%I:%M %p"), time_slot))

            # 3. Find the closest available time within allowed window
            requested_dt = datetime.strptime(desired_time, "%H:%M")
            closest_time_slot = None
            min_diff = timedelta(minutes=9999)

            # Define allowed time window (15 minutes before to 30 minutes after)
            earliest_time = requested_dt - timedelta(minutes=15)
            latest_time = requested_dt + timedelta(minutes=30)
            
            # Cap latest_time at 23:59 to avoid next-day wrap
            if latest_time.day > requested_dt.day:
                latest_time = requested_dt.replace(hour=23, minute=59, second=0, microsecond=0)
            
            for time_slot_time, time_slot in time_slots_times:
                self.log_message(f"Checking time slot: {time_slot_time}")
                if not (earliest_time <= time_slot_time <= latest_time):
                    self.log_message(f"Time slot {time_slot_time} is not in the allowed window")
                    continue
                
                diff = abs((time_slot_time - requested_dt).total_seconds())
                if diff < min_diff.total_seconds():
                    min_diff = timedelta(seconds=diff)
                    closest_time_slot = (time_slot_time, time_slot)
            
            if not closest_time_slot:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            # 4. Click the closest available time slot
            await closest_time_slot[1].click()
            await page.wait_for_timeout(10000)
            
            success_msg = build_reservation_success_message(f"✅ Time {closest_time_slot[0]} selected successfully")
            self.log_message(success_msg)
            return ActionResult(extracted_content=success_msg)
            
        except Exception as e:
            error_msg = f"❌ Error selecting from available time slots: {e}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)

    async def select_seating_option(self, page) -> ActionResult:
        """Select seating option."""
        try:

            PAGE_ID = "seating-options"

            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefixes}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            if PAGE_ID not in page.url:
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} seating options page"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            # 1. Get the seating options
            seating_options_selector = 'button[data-test="seatingOption-default-button"]' 
            seating_options = page.locator(seating_options_selector)

            if await seating_options.count() == 0:
                error_msg = f"❌ Could not find seating options"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)
           
            # 2. Click the seating option
            await seating_options.first.click()
            # Trigger page change with wait for timeout
            await page.wait_for_timeout(3000)

            success_msg = build_reservation_success_message(f"✅ Seating option selected successfully")
            self.log_message(success_msg)
            return ActionResult(extracted_content=success_msg)
        
        except Exception as e:
            error_msg = f"❌ Error selecting seating option: {e}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)
    
    async def select_reservation_type(self, page) -> ActionResult:
        """Select reservation type."""
        try:
            PAGE_ID = "booking/specials"

            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefixes}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            if PAGE_ID not in page.url:
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation type page"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            # 1. Get the reservation type
            default_reservation_type_selector = 'button[data-test="noSpecialLink"]'
            default_reservation_type = page.locator(default_reservation_type_selector)

            if await default_reservation_type.count() == 0:
                error_msg = f"❌ Could not find default reservation type"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)
            
            # 2. Click the default reservation type
            await default_reservation_type.first.click()
            await page.wait_for_timeout(3000)

            success_msg = build_reservation_success_message(f"✅ Reservation type selected successfully")
            self.log_message(success_msg)
            return ActionResult(extracted_content=success_msg)

        except Exception as e:
            error_msg = f"❌ Error selecting reservation type: {e}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)
    
    async def update_reservation_contact_info(self, page, first_name: str, last_name: str, 
                                            phone: str, email: str) -> ActionResult:
        """Update contact information for the reservation."""
        
        try:
            PAGE_ID = "booking/details"
            
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefixes}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            if PAGE_ID not in page.url:
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation details page"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            # Parse the phone number to extract country code and national number
            parsed_result = parse_phone_number(phone)

            if parsed_result["error"] is not None:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["invalid_phone_number"])
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            country_code = parsed_result["iso_country_code"]
            national_number = parsed_result["national_number"]

            await page.wait_for_timeout(3000)

            # 1. Get the contact info fields
            selectors_and_values = {
                "first_name": ("input[id='firstName']", first_name),
                "last_name": ("input[id='lastName']", last_name),
                "phone_country_code": ("select[id='phoneNumberCountryCode']", country_code),
                "phone_number": ("input[id='phoneNumber']", national_number),
                "email": ("input[id='email']", email),
            }

            credit_card_field_selector = "div[id='credit-card-number-field']"
            # 2. If credit card is required, return error
            if await page.locator(credit_card_field_selector).count() > 0:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["credit_card_info_required"])
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)
            
            # 3. Fill the contact info fields
            # Define wait time once
            WAIT_TIME = 2000

            # Fill the contact info fields
            for field, (selector, value) in selectors_and_values.items():
                try: 
                    locator = page.locator(selector)

                    # Wait for the element to become visible before interacting
                    await locator.wait_for(state="visible", timeout=WAIT_TIME)

                    if await locator.is_disabled():
                        self.log_message(f"Field {field} is disabled, skipping...")
                        continue

                    if field == "phone_country_code":
                        await locator.select_option(country_code)
                    elif field == "phone_number":
                        await locator.fill(national_number)
                    else:
                        await locator.fill(value)

                except Exception as e:
                    error_msg = f"⚠️ Error filling contact info field {field}: {e}"
                    self.log_message(error_msg)
                    continue
            
            # 4. Check required checkboxes
            await self.check_required_checkboxes(page)

            success_msg = build_reservation_success_message(f"✅ Contact info filled successfully: {first_name} {last_name}, {country_code} {national_number}, {email}")
            self.log_message(success_msg)
            return ActionResult(extracted_content=success_msg)


        except Exception as e:
            error_msg = f"❌ Error updating reservation contact info: {e}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)

    async def check_required_checkboxes(self, page) -> ActionResult:
        """Check required checkboxes."""
        try:
            PAGE_ID = "booking/details"
            
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefixes}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            if PAGE_ID not in page.url:
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation details page"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)
            
            # 1. Locate the heading with text "Required:"
            required_heading = page.locator('h4', has_text="Required:")
            if await required_heading.count() == 0:
                self.log_message("No required section found — skipping.")
                return ActionResult(extracted_content="No required section found — skipping.")

            # 2. Get the parent div that wraps the required section
            required_container = required_heading.locator('xpath=..')

            # 3. Find all checkbox inputs inside the container
            checkboxes = required_container.locator('input[type="checkbox"]')

            count = await checkboxes.count()
            self.log_message(f"Found {count} required checkbox(es). Checking them...")

            for i in range(count):
                cb = checkboxes.nth(i)
                checked = await cb.is_checked()
                if not checked:
                    # Find the associated label and click it
                    label = cb.locator('xpath=ancestor::label[1]')
                    self.log_message(f"Clicking label for checkbox {i}...")
                    await label.click()

            self.log_message("Done checking required checkboxes.")

            success_msg = build_reservation_success_message(f"✅ Required checkboxes checked successfully")
            self.log_message(success_msg)
            return ActionResult(extracted_content=success_msg)
        except Exception as e:
            error_msg = f"❌ Error checking required checkboxes: {e}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)
    
    async def finalize_booking(self, page) -> ActionResult:
        """
        Provider-specific final booking steps.
        This should handle clicking the final book button and confirming the reservation.
        """
        try:
            PAGE_ID = "booking/details"
            PAGE_ID_CONFIRMATION = "booking/confirmation"
            WAIT_TIME = 5000  # 5 seconds max wait

            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefixes}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            if PAGE_ID not in page.url:
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation details page"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)

            final_book_button_selector = "button[data-test='complete-reservation-button']"
            spinner_selector = "div[data-test='spinner']"

            final_book_button = page.locator(final_book_button_selector)

            # 1. Wait for button to be enabled (aria-disabled="false")
            await final_book_button.wait_for(state="visible", timeout=WAIT_TIME)
            

            # 2. Click the final book button
            await final_book_button.click()


            # 4. Check if reservation is complete by checking the URL
            try:
                await page.wait_for_url(f"**/{PAGE_ID_CONFIRMATION}*", timeout=WAIT_TIME)
                if PAGE_ID_CONFIRMATION in page.url:
                    success_msg = build_reservation_success_message("✅ Reservation completed successfully")
                    self.log_message(success_msg)
                    return ActionResult(extracted_content=success_msg)
            except Exception as e:
                self.log_message(f"Confirmation page not found, continuing...")

            # fallback: reservation not confirmed
            error_msg = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)

        except Exception as e:
            error_msg = f"❌ Exception during finalizing booking: {e}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)
   
    async def reserve_with_provider(self, page, party_size: int, date: str, time_24h: str,
                                  first_name: str, last_name: str, phone: str, email: str) -> ActionResult:
        """
        Complete reservation flow for this provider.
        This is the main method that orchestrates the entire reservation process.
        """
        
        try:

            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefixes}"
                self.log_message(error_msg)
                return ActionResult(extracted_content=error_msg)
            
            # 1. Select party size
            party_size_result = await self.select_reservation_party_size(page, party_size)
            if party_size_result.extracted_content and not party_size_result.extracted_content.startswith("✅"):
                return party_size_result
            
            await page.wait_for_timeout(1000)

            # 2. Select date
            date_result = await self.select_reservation_date(page, date)
            if date_result.extracted_content and not date_result.extracted_content.startswith("✅"):
                return date_result
            
            await page.wait_for_timeout(1000)

            # 3. Select time
            time_result = await self.select_reservation_time(page, time_24h)
            if time_result.extracted_content and not time_result.extracted_content.startswith("✅"):
                return time_result

            await page.wait_for_timeout(1000)

            # 4. Select from available time slots
            time_slot_result = await self.select_from_available_time_slots(page, time_24h)
            if time_slot_result.extracted_content and not time_slot_result.extracted_content.startswith("✅"):
                return time_slot_result
            
            await page.wait_for_timeout(1000)

            # 5. Select seating option
            await self.select_seating_option(page)
            await page.wait_for_timeout(1000)
            
            # 6. Select reservation type
            await self.select_reservation_type(page)
            await page.wait_for_timeout(1000)
            
            # 7. Update contact info
            contact_info_result = await self.update_reservation_contact_info(page, first_name, last_name, phone, email)
            if contact_info_result.extracted_content and not contact_info_result.extracted_content.startswith("✅"):
                return contact_info_result
            
            # 8. Finalize booking
            finalize_result = await self.finalize_booking(page)
            if finalize_result.extracted_content and not finalize_result.extracted_content.startswith("✅"):
                return finalize_result
            
            success_msg = build_reservation_success_message(RESERVATION_SUCCESSES["reservation_complete"].format(party_size=party_size, date=date, time_24h=time_24h))
            self.log_message(success_msg)
            return ActionResult(extracted_content=success_msg, success=True, is_done=True)
        except Exception as e:
            error_msg = f"❌ Error reserving with provider: {e}"
            self.log_message(error_msg)
            return ActionResult(extracted_content=error_msg)
    