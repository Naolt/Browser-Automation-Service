from browser_use import ActionResult
from openai._utils import parse_date
from models.reservation_models import ProviderType
from services.actions.provider.base_provider import BaseReservationProvider
from services.actions.utils import RESERVATION_ERRORS, RESERVATION_SUCCESSES, build_reservation_failure_message, build_reservation_success_message, parse_phone_number

class SevenRoomsProvider(BaseReservationProvider):
    """
    SevenRooms provider
    """
    
    def __init__(self):
        discovery_patterns = [  r"sevenrooms\.com",
            r"seven\s*rooms",
            r"7rooms"
        ]
        super().__init__("seven_rooms", ["https://www.sevenrooms.com/"], ProviderType.SEVENROOMS, discovery_patterns=discovery_patterns)

    
    def _month_to_number(self, month_name: str) -> int:
        """Convert month name to number for comparison"""
        months = {
            "January": 1, "February": 2, "March": 3, "April": 4,
            "May": 5, "June": 6, "July": 7, "August": 8,
            "September": 9, "October": 10, "November": 11, "December": 12
        }
        return months.get(month_name, 0)
    
    async def _select_country_code(self, page, target_country_code: str) -> ActionResult:
        """
        Select the country code from the dropdown.
        """
        try:
            print(f"[seven_rooms_country_code] Selecting country code: {target_country_code}")
            
            # Step 1: Click on the country code dropdown/flag (using more generic selector)
            # Try multiple selectors for better reliability
            country_dropdown_selectors = [
                'div.flag',  # More generic
                'div.sc-cGNDeh.jNGIOk'
               ]
            
            country_dropdown = None
            for selector in country_dropdown_selectors:
                dropdown = page.locator(selector)
                if await dropdown.count() > 0:
                    country_dropdown = dropdown.first
                    print(f"[seven_rooms_country_code] Found dropdown with selector: {selector}")
                    break
            
            if not country_dropdown:
                error_msg = "❌ Country code dropdown not found"
                print(f"[seven_rooms_country_code] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            await country_dropdown.click()
            await page.wait_for_timeout(500)  # Wait for dropdown to open
            
            
            # Wait for all country options to appear
            await page.wait_for_selector('div.flag + span + span')

            # Get all country code spans (those that follow the flag and country name spans)
            country_code_spans = page.locator('div.flag + span + span')

            count = await country_code_spans.count()
            print(f"[seven_rooms_country_code] Found {count} country code spans")

            for i in range(count):
                span = country_code_spans.nth(i)
                code_text = (await span.inner_text()).strip()
                print(f"[seven_rooms_country_code] Checking span {i+1}: {code_text}")
                
                if code_text == target_country_code:
                    # Click the grandparent div of the matched span
                    option_container = span.locator('xpath=..')
                    await option_container.click()
                    await page.wait_for_timeout(500)
                    print(f"✅ Selected country code: {target_country_code}")
                    return ActionResult(extracted_content=f"✅ Selected: {target_country_code}")


            self.log_message(f"[seven_rooms_country_code] No exact match found, trying partial match")
            # Step 4: Try partial match as last resort
            for i in range(await country_code_spans.count()):
                span = country_code_spans.nth(i)
                code_text = await span.inner_text()
                
                if target_country_code in code_text:
                    parent_option = span.locator('xpath=..')
                    await parent_option.click()
                    await page.wait_for_timeout(500)
                    
                    success_msg = f"✅ Country code {target_country_code} selected via partial match"
                    print(f"[seven_rooms_country_code] {success_msg}")
                    return ActionResult(extracted_content=success_msg)
            
            error_msg = build_reservation_failure_message(RESERVATION_ERRORS["invalid_phone_number"])
            print(f"[seven_rooms_country_code] {error_msg}")
            return ActionResult(extracted_content=error_msg)
                
        except Exception as e:
            error_msg = f"❌ Error selecting country code {target_country_code}: {str(e)}"
            print(f"[seven_rooms_country_code] {error_msg}")
            return ActionResult(extracted_content=error_msg)
    
    async def select_reservation_party_size(self, page, party_size: int) -> ActionResult:
        """
        Selects the party size for the reservation.
        selector data-test="sr-guest-count-button" for opening the party size selector
        to select the party size, we need to check two things: hence the selector is id="sr-selectdesiredpartysize-[party_size]"
        - after selecting it check if the aria-lable has value if so click it and return success
        - if not, return failure
        - if the party size is not available, return failure
        - if the party size is available, return success
        """
        try:
            print(f"[seven_rooms_party_size] Trying to select party size: {party_size}")
            
            # Check if we're on the correct page
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefix}"
                print(f"[seven_rooms_party_size] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            # Close any popups first
            await self.close_popup_by_selector(page=page, selector='[aria-label="Close"]')
            
            # Step 1: Click the party size selector button to open the dropdown
            party_size_button = page.locator('[data-test="sr-guest-count-button"]')
            
            if await party_size_button.count() == 0:
                error_msg = f"❌ Could not find party size selector button"
                print(f"[seven_rooms_party_size] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            await party_size_button.click()
            await page.wait_for_timeout(500)  # Wait for dropdown to open
            
            # Step 2: Look for the specific party size option
            # The ID is just an index, we need to find the button with the correct party size in aria-label or text
            party_size_option = None
            
            # Get all party size options
            all_party_options = page.locator('button[id^="sr-selectdesiredpartysize-"]')
            
            for i in range(await all_party_options.count()):
                option = all_party_options.nth(i)
                aria_label = await option.get_attribute("aria-label")
                button_text = await option.inner_text()
                
                print(f"[seven_rooms_party_size] Checking option {i+1}: aria-label='{aria_label}', text='{button_text}'")
                
                # Check if this option matches our desired party size
                if (aria_label and aria_label.strip() == str(party_size)) or (button_text and button_text.strip() == str(party_size)):
                    party_size_option = option
                    print(f"[seven_rooms_party_size] Found matching party size option: {party_size}")
                    break
            
            if not party_size_option:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["party_size_not_available"])
                print(f"[seven_rooms_party_size] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            
            # Step 3: Click the party size option
            await party_size_option.scroll_into_view_if_needed()
            await party_size_option.click()
            await page.wait_for_timeout(500)  # Wait for selection to register
            
            # Step 4: Verify the selection was successful
            # Check if the button still has the selected state or if we can verify the selection
            success_msg = f"✅ Party size {party_size} selected successfully"
            print(f"[seven_rooms_party_size] {success_msg}")
            return ActionResult(extracted_content=success_msg)
            
        except Exception as e:
            error_msg = f"❌ Error selecting party size {party_size}: {str(e)}"
            print(f"[seven_rooms_party_size] {error_msg}")
            return ActionResult(extracted_content=error_msg)
    
    async def select_reservation_date(self, page, date: str) -> ActionResult:
        """
        selector data-test="sr-calendar-date-button" for opening the calendar
        which looks like this:
        <button disabled="" type="button" data-test="sr-calendar-date-picker-button" ><div>August 2025</div><div ></div></button>
        # selector <td> tag with role="button" for selecting the dates
        which looks like this:
        <td tabindex="0" role="button" aria-label="Wednesday, July 9th 2025, Available">9</td>
        # we need to click on the date to select it. 

        calendar control selectors for next month and prev month:
        <button aria-label="increment month" data-test="sr-increment-arrow"></button>
        <button aria-label="decrement month" data-test="sr-decrement-arrow"></button>
        """
        try:
            print(f"[seven_rooms_date] Starting date selection for: {date}")
            
            # Check if we're on the correct page
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefix}"
                print(f"[seven_rooms_date] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            # Close any popups first
            await self.close_popup_by_selector(page=page, selector='[aria-label="Close"]')
            
            # Parse the target date
            target_dt = parse_date(date)
            target_month = target_dt.strftime("%B")  # e.g., "August"
            target_year = target_dt.year
            target_day = target_dt.day
            print(f"[seven_rooms_date] Target: {target_month} {target_year}, Day: {target_day}")
            
            # Step 1: Open the calendar widget
            calendar_button = page.locator('[data-test="sr-calendar-date-button"]')
            
            if await calendar_button.count() == 0:
                error_msg = "❌ Could not find calendar date button"
                print(f"[seven_rooms_date] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            await calendar_button.click()
            print("[seven_rooms_date] Clicked calendar button")
            
            # Wait for calendar to open
            try:
                await page.wait_for_selector('td[role="button"]', timeout=5000)
                print("[seven_rooms_date] Calendar widget opened")
            except Exception:
                error_msg = "❌ Calendar widget did not open"
                print(f"[seven_rooms_date] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            await page.wait_for_timeout(500)
            
            # Step 2: Navigate to the correct month/year
            next_button = page.locator('[data-test="sr-increment-arrow"]')
            prev_button = page.locator('[data-test="sr-decrement-arrow"]')
            
            # Get current month/year from the calendar header
            calendar_header = page.locator('[data-test="sr-calendar-date-picker-button"] div').first
            
            for _ in range(12):  # Prevent infinite loop
                try:
                    header_text = await calendar_header.inner_text()
                    print(f"[seven_rooms_date] Current calendar header: {header_text}")
                    
                    # Parse header text (e.g., "August 2025")
                    current_month, current_year = header_text.strip().split()
                    current_year = int(current_year)
                    
                    if current_month == target_month and current_year == target_year:
                        print(f"[seven_rooms_date] Navigated to correct month: {current_month} {current_year}")
                        break
                    
                    # Navigate to target month
                    if (current_year < target_year) or (current_year == target_year and self._month_to_number(current_month) < self._month_to_number(target_month)):
                        await next_button.click()
                        print("[seven_rooms_date] Clicked next month")
                    else:
                        await prev_button.click()
                        print("[seven_rooms_date] Clicked previous month")
                    
                    await page.wait_for_timeout(400)
                    
                except Exception as e:
                    print(f"[seven_rooms_date] Error parsing header: {str(e)}")
                    return ActionResult(extracted_content=f"❌ Error parsing calendar header: {str(e)}")
            else:
                error_msg = f"❌ Could not navigate to {target_month} {target_year} in calendar"
                print(f"[seven_rooms_date] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            # Step 3: Find and select the target date
            # Look for date elements with role="button" and aria-label containing the target day
            date_elements = page.locator('td[role="button"]')
            target_date_found = False
            
            for i in range(await date_elements.count()):
                date_element = date_elements.nth(i)
                aria_label = await date_element.get_attribute("aria-label")
                
                if aria_label and "Available" in aria_label:
                    # Extract the day number from aria-label more precisely
                    # aria-label format: "Wednesday, July 9th 2025, Available"
                    import re
                    day_match = re.search(r'(\d{1,2})(?:st|nd|rd|th)?', aria_label)
                    
                    if day_match:
                        day_in_label = int(day_match.group(1))
                        print(f"[seven_rooms_date] Checking date: {aria_label} → Day: {day_in_label}")
                        
                        if day_in_label == target_day:
                            print(f"[seven_rooms_date] Found matching available date: {aria_label}")
                            await date_element.scroll_into_view_if_needed()
                            await date_element.click()
                            await page.wait_for_timeout(500)
                            target_date_found = True
                            break
            
            if target_date_found:
                success_msg = f"✅ Date {date} selected successfully"
                print(f"[seven_rooms_date] {success_msg}")
                return ActionResult(extracted_content=success_msg)
                
            error_msg = build_reservation_failure_message(RESERVATION_ERRORS["date_not_available"])
            print(f"[seven_rooms_date] Date {target_day} found but not available: {aria_label}")
            return ActionResult(extracted_content=error_msg)
            
                
        except Exception as e:
            error_msg = f"❌ Error selecting date {date}: {str(e)}"
            print(f"[seven_rooms_date] {error_msg}")
            return ActionResult(extracted_content=error_msg)
    
    async def select_reservation_time(self, page, desired_time: str) -> ActionResult:
        """
        Button to click to open the time selector:
        <button type="button" data-test="sr-time-button"><div>09:00</div><div>Time</div></button>

        After clicking the time button, the time selector will open. and the time options are like:
         <button id="sr-selectdesiredtime-15" aria-label="09:00" tabindex="0">09:00</button>

        if the time is not available, the aria-label will be empty.

        """
        try:
            print(f"[seven_rooms_time] Starting time selection for: {desired_time}")
            
            # Check if we're on the correct page
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefix}"
                print(f"[seven_rooms_time] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            # Close any popups first
            await self.close_popup_by_selector(page=page, selector='[aria-label="Close"]')
            
            # Step 1: Parse user-requested time
            from datetime import datetime, timedelta
            from services.actions.utils import round_up_to_next_half_hour, to_time_string
            import re
            
            requested_dt = datetime.strptime(desired_time, "%H:%M")
            dropdown_time_dt = round_up_to_next_half_hour(requested_dt)
            dropdown_time_str = to_time_string(dropdown_time_dt)
            
            print(f"[seven_rooms_time] Requested: {desired_time}, Dropdown base: {dropdown_time_str}")
            
            # Step 2: Open the time selector
            time_button = page.locator('[data-test="sr-time-button"]')
            
            if await time_button.count() == 0:
                error_msg = "❌ Could not find time selector button"
                print(f"[seven_rooms_time] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            await time_button.click()
            print("[seven_rooms_time] Clicked time selector button")
            
            # Wait for time options to appear
            try:
                await page.wait_for_selector('button[id^="sr-selectdesiredtime-"]', timeout=5000)
                print("[seven_rooms_time] Time selector opened")
            except Exception:
                error_msg = "❌ Time selector did not open"
                print(f"[seven_rooms_time] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            await page.wait_for_timeout(500)
            
            # Step 3: Get all time options
            time_options = page.locator('button[id^="sr-selectdesiredtime-"]')
            valid_time_buttons = []
            
            print(f"[seven_rooms_time] Found {await time_options.count()} time options")
            
            for i in range(await time_options.count()):
                time_option = time_options.nth(i)
                aria_label = await time_option.get_attribute("aria-label")
                button_text = await time_option.inner_text()
                
                print(f"[seven_rooms_time] Checking option {i+1}: aria-label='{aria_label}', text='{button_text}'")
                
                # Check if aria-label has a value (indicating availability)
                if aria_label and aria_label.strip() != "":
                    # Extract time from aria-label (e.g., "09:00")
                    if re.match(r'^\d{1,2}:\d{2}$', aria_label):
                        valid_time_buttons.append((aria_label, time_option))
                        print(f"[seven_rooms_time] Valid time found: {aria_label}")
                else:
                    print(f"[seven_rooms_time] Skipping unavailable time: {button_text}")
            
            if not valid_time_buttons:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                print(f"[seven_rooms_time] No available times found")
                return ActionResult(extracted_content=error_msg)
            
            # Step 4: Find the closest available time within allowed window
            closest_button = None
            min_diff = timedelta(minutes=9999)
            
            # Define allowed time window (15 minutes before to 30 minutes after)
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
            
            # Step 5: Click the closest available button
            if closest_button:
                print(f"[seven_rooms_time] ✅ Closest time found: {closest_button[0]}")
                await closest_button[1].scroll_into_view_if_needed()
                await page.wait_for_timeout(200)  # 200ms pause before clicking
                await closest_button[1].click()
                await page.wait_for_timeout(500)  # Wait for selection to register
                
                success_msg = f"✅ Time {closest_button[0]} selected successfully"
                print(f"[seven_rooms_time] {success_msg}")
                return ActionResult(extracted_content=success_msg)
            else:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                print(f"[seven_rooms_time] ❌ No available time near {desired_time}")
                return ActionResult(extracted_content=error_msg)
                
        except Exception as e:
            error_msg = f"❌ Error selecting time {desired_time}: {str(e)}"
            print(f"[seven_rooms_time] {error_msg}")
            return ActionResult(extracted_content=error_msg)

    async def select_from_available_time_slots(self, page, desired_time: str) -> ActionResult:
        """
        Handle time slot selection that appears after clicking the search button.
        This method is called when the search button shows available time slots.
        
        The time slots appear as:
        <button data-test="sr-timeslot-button"><div>13:00</div><div>Lunch (Indoor)<i class="sc-epRvzc huJXen fa fa-info-circle fa-fw" aria-hidden="true"></i></div></button>
        
        We need to find the time slot that matches the desired time and click it.
        """
        try:
            print(f"[seven_rooms_time_slots] Looking for time slot: {desired_time}")
            
            # Check if we're on the correct page
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefix}"
                print(f"[seven_rooms_time_slots] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            # Wait for the availability alert to appear first
            try:
                await page.wait_for_selector('div[role="alert"][aria-label*="Availability found"]', timeout=10000)
                print("[seven_rooms_time_slots] Availability alert found")
            except Exception:
                # Check if no availability message appears
                no_availability = page.locator('div:has-text("Unfortunately there is no availability at the selected time.")')
                if await no_availability.count() > 0:
                    error_msg = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                    print(f"[seven_rooms_time_slots] No availability at selected time")
                    return ActionResult(extracted_content=error_msg)
                else:
                    error_msg = "❌ Availability alert did not appear after search"
                    print(f"[seven_rooms_time_slots] {error_msg}")
                    return ActionResult(extracted_content=error_msg)
            
            await page.wait_for_timeout(1000)  # Wait for all slots to load
            
            # Find the parent container that contains both the alert and time slots for the current date
            # This ensures we're selecting from the correct date's available times
            alert_element = page.locator('div[role="alert"][aria-label*="Availability found"]').first
            
            # Find the parent container that contains both the alert and time slots
            parent_container = alert_element.locator('xpath=..')
            
            # Get time slot buttons within the same parent container as the alert
            time_slot_buttons = parent_container.locator('[data-test="sr-timeslot-button"]')
            available_slots = []
            
            print(f"[seven_rooms_time_slots] Found {await time_slot_buttons.count()} time slots")
            
            # Parse the desired time
            from datetime import datetime, timedelta
            
            try:
                desired_dt = datetime.strptime(desired_time, "%H:%M")
            except ValueError:
                error_msg = f"❌ Invalid time format: {desired_time}"
                print(f"[seven_rooms_time_slots] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            # Collect all available time slots
            for i in range(await time_slot_buttons.count()):
                slot_button = time_slot_buttons.nth(i)
                
                # Get the time from the first div (e.g., "13:00")
                time_div = slot_button.locator('div').first
                slot_time_text = await time_div.inner_text()
                
                print(f"[seven_rooms_time_slots] Slot {i+1}: {slot_time_text}")
                
                # Parse the time
                try:
                    slot_time = datetime.strptime(slot_time_text.strip(), "%H:%M")
                    available_slots.append((slot_time, slot_button))
                except ValueError:
                    print(f"[seven_rooms_time_slots] Skipping invalid time format: {slot_time_text}")
                    continue
            
            if not available_slots:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                print(f"[seven_rooms_time_slots] No valid time slots found")
                return ActionResult(extracted_content=error_msg)
            
            # Find the closest available time within allowed window
            closest_slot = None
            min_diff = timedelta(minutes=9999)
            
            # Define allowed time window (15 minutes before to 30 minutes after)
            earliest_time = desired_dt - timedelta(minutes=15)
            latest_time = desired_dt + timedelta(minutes=30)
            
            # Cap latest_time at 23:59 to avoid next-day wrap
            if latest_time.day > desired_dt.day:
                latest_time = desired_dt.replace(hour=23, minute=59, second=0, microsecond=0)
            
            for slot_time, slot_button in available_slots:
                # Check if within allowed window
                if not (earliest_time <= slot_time <= latest_time):
                    continue
                
                # Calculate time difference
                diff = abs((slot_time - desired_dt).total_seconds())
                if diff < min_diff.total_seconds():
                    min_diff = timedelta(seconds=diff)
                    closest_slot = (slot_time, slot_button)
            
            # Click the closest available slot
            if closest_slot:
                slot_time, slot_button = closest_slot
                slot_time_str = slot_time.strftime("%H:%M")
                
                print(f"[seven_rooms_time_slots] ✅ Closest time slot found: {slot_time_str}")
                
                # Scroll into view and click
                await slot_button.scroll_into_view_if_needed()
                await page.wait_for_timeout(200)  # 200ms pause before clicking
                await slot_button.click()
                await page.wait_for_timeout(1000)  # Wait for modal to appear
                
                # Check if the time slot modal appeared
                modal = page.locator('[data-test="sr-time-slot-popup-modal"]')
                if await modal.count() > 0:
                    # Click the select button in the modal
                    select_button = modal.locator('[data-test="sr-time-slot-popup-modal-select-button"]')
                    if await select_button.count() > 0:
                        await select_button.click()
                        await page.wait_for_timeout(500)
                        
                        success_msg = f"✅ Time slot {slot_time_str} selected successfully"
                        print(f"[seven_rooms_time_slots] {success_msg}")
                        return ActionResult(extracted_content=success_msg)
                    else:
                        error_msg = "❌ Select button not found in time slot modal"
                        print(f"[seven_rooms_time_slots] {error_msg}")
                        return ActionResult(extracted_content=error_msg)
                else:
                    # If no modal, the selection might be direct
                    success_msg = f"✅ Time slot {slot_time_str} selected successfully"
                    print(f"[seven_rooms_time_slots] {success_msg}")
                    return ActionResult(extracted_content=success_msg)
            else:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["time_not_available"])
                print(f"[seven_rooms_time_slots] ❌ No available time slot near {desired_time}")
                return ActionResult(extracted_content=error_msg)
                
        except Exception as e:
            error_msg = f"❌ Error selecting time slot {desired_time}: {str(e)}"
            print(f"[seven_rooms_time_slots] {error_msg}")
            return ActionResult(extracted_content=error_msg)
    
    async def select_reservation_provider(self, page) -> ActionResult:
        """
        Handle provider-specific popups or selections for SevenRooms.
        """
        try:
            print("[seven_rooms_provider] Checking for provider-specific popups...")
            
            # SevenRooms might have specific popups or selections
            # For now, return success as this is provider-specific
            success_msg = "ℹ️ No provider-specific popups found for SevenRooms"
            print(f"[seven_rooms_provider] {success_msg}")
            return ActionResult(extracted_content=success_msg)
            
        except Exception as e:
            error_msg = f"❌ Error handling provider popups: {str(e)}"
            print(f"[seven_rooms_provider] {error_msg}")
            return ActionResult(extracted_content=error_msg)
      
    async def update_reservation_contact_info(self, page, first_name: str, last_name: str, phone: str, email: str) -> ActionResult:
        """
        Update the reservation contact info.
         here are the selectors:
            - 1. ✅ First Name: input[aria-label="First Name"]
            - 2. ✅ Last Name: input[aria-label="Last Name"]
            - 3. ✅ Email Address: input[aria-label="Email"]
            - 4. ✅ Phone Number with country code: 
                - Country Code:
                    1. First click on the country code input field with selector: <div class="sc-ksCcjW bvAIOS flag flag-ae"></div>
                    2. Then extract country code from the provided phone number and look for it in option list. the option list looks like this:
                    <div class="sc-dNckAz blPvun"><div class="sc-SSKRe jA-dcLj"><div class="sc-ksCcjW bvAIOS flag flag-dz"></div><span class="sc-cYxjnA kga-dHK">Algeria (‫الجزائر‬‎)</span><span class="sc-fDinKg gIWriR">+213</span></div></div>
                - Phone Number: input[aria-label="Phone Number"]
            - If credit card info is requested, return error message: "❌ Credit card info is required"
               - Selector: input[data-test="sr-cc-number"]
        """
        try:
            print(f"[seven_rooms_contact] Updating contact info: {first_name} {last_name}, {phone}, {email}")
            
            # Check if we're on the correct page
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefix}"
                print(f"[seven_rooms_contact] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            # Wait for the contact form to load
            await page.wait_for_timeout(2000)
            
            # Close any popups first
            await self.close_popup_by_selector(page=page, selector='[aria-label="Close"]')

            # Check if credit card info is required
            if await page.locator('input[data-test="sr-cc-number"]').count() > 0:
                # check if aria-required attribute is present not necessarily true
                aria_required = await page.locator('input[data-test="sr-cc-number"]').get_attribute("aria-required")
                if aria_required is not None:
                    error_msg = build_reservation_failure_message(RESERVATION_ERRORS["credit_card_info_required"])
                    print(f"[seven_rooms_contact] {error_msg}")
                    return ActionResult(extracted_content=error_msg)
            
            # Step 1: Fill First Name
            first_name_input = page.locator('input[aria-label="First Name"]')
            if await first_name_input.count() > 0:
                await first_name_input.fill(first_name)
                print(f"[seven_rooms_contact] Filled first name: {first_name}")
            else:
                error_msg = "❌ First name input field not found"
                print(f"[seven_rooms_contact] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            await page.wait_for_timeout(300)
            
            # Step 2: Fill Last Name
            last_name_input = page.locator('input[aria-label="Last Name"]')
            if await last_name_input.count() > 0:
                await last_name_input.fill(last_name)
                print(f"[seven_rooms_contact] Filled last name: {last_name}")
            else:
                error_msg = "❌ Last name input field not found"
                print(f"[seven_rooms_contact] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            await page.wait_for_timeout(300)
            
            # Step 3: Fill Email Address
            email_input = page.locator('input[aria-label="Email"]')
            if await email_input.count() > 0:
                await email_input.fill(email)
                print(f"[seven_rooms_contact] Filled email: {email}")
            else:
                error_msg = "❌ Email input field not found"
                print(f"[seven_rooms_contact] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            await page.wait_for_timeout(300)
            
            # Step 4: Handle Phone Number with Country Code
            print(f"[seven_rooms_contact] Processing phone number: {phone}")
            
            # Parse the phone number to extract country code and national number
            parsed_result = parse_phone_number(phone)

            if parsed_result["error"] is not None:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["invalid_phone_number"])
                print(f"[seven_rooms_contact] {error_msg}")
                return ActionResult(extracted_content=error_msg)

            country_code = parsed_result["country_prefix"]
            national_number = parsed_result["national_number"]

            if country_code is None or national_number is None:
                error_msg = build_reservation_failure_message(RESERVATION_ERRORS["invalid_phone_number"])
                print(f"[seven_rooms_contact] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            print(f"[seven_rooms_contact] Parsed phone - Country: {country_code}, National: {national_number}")
            
            # Step 4a: Select Country Code
            country_result = await self._select_country_code(page=page, target_country_code=country_code)
            if country_result.extracted_content and not country_result.extracted_content.startswith("✅") and not country_result.extracted_content.startswith("ℹ️"):
                return country_result
            
            await page.wait_for_timeout(500)
            
            # Step 4b: Fill Phone Number (national number without country code)
            phone_input = page.locator('input[aria-label="Phone Number"]')
            if await phone_input.count() > 0:
                await phone_input.fill(country_code + national_number)
                print(f"[seven_rooms_contact] Filled phone number: {national_number}")
            else:
                error_msg = "❌ Phone number input field not found"
                print(f"[seven_rooms_contact] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            await page.wait_for_timeout(500)
            
            success_msg = f"✅ Contact info filled successfully: {first_name} {last_name}, {country_code} {national_number}, {email}"
            print(f"[seven_rooms_contact] {success_msg}")
            return ActionResult(extracted_content=success_msg)
                
        except Exception as e:
            error_msg = f"❌ Error filling contact info: {str(e)}"
            print(f"[seven_rooms_contact] {error_msg}")
            return ActionResult(extracted_content=error_msg)
    
    async def finalize_booking(self, page) -> ActionResult:
        """
        Finalize the booking for SevenRooms.
        """
        try:
            print("[seven_rooms_finalize] Finalizing SevenRooms booking...")
            
            # Step 1: Submit the reservation
            submit_result = await self.submit_reservation(page)
            if submit_result.extracted_content and not submit_result.extracted_content.startswith("✅"):
                return submit_result
            
            # Step 2: Check for confirmation
            confirmation_result = await self.check_reservation_confirmation(page)
            return confirmation_result
            
        except Exception as e:
            error_msg = f"❌ Error finalizing booking: {str(e)}"
            print(f"[seven_rooms_finalize] {error_msg}")
            return ActionResult(extracted_content=error_msg)

    async def submit_reservation(self, page) -> ActionResult:
        """
        Submit the reservation after contact info is filled.
        """
        try:
            print("[seven_rooms_submit] Submitting reservation...")
            
            # Step 1: Check for custom checkout policy checkbox
            custom_policy_checkbox = page.locator('button[data-test="sr-agreedCustomCheckoutPolicy-checkbox"]')
            if await custom_policy_checkbox.count() > 0:
                print("[seven_rooms_submit] Found custom checkout policy checkbox, clicking it...")
                
                # Check if it's already selected by looking for the checkmark icon
                checkmark_icon = custom_policy_checkbox.locator('i.fa.fa-check.fa-fw')
                is_checked = await checkmark_icon.count() > 0
                
                # If not already checked, click it
                if not is_checked:
                    await custom_policy_checkbox.click()
                    await page.wait_for_timeout(500)  # Wait for checkbox to register
                    print("[seven_rooms_submit] Custom checkout policy checkbox clicked")
                else:
                    print("[seven_rooms_submit] Custom checkout policy checkbox already checked")
            else:
                print("[seven_rooms_submit] No custom checkout policy checkbox found")
            
            await page.wait_for_timeout(500)  # Brief pause before proceeding
            
            # Step 2: Click the submit button
            submit_button = page.locator('button[data-test="sr-submit-button"]')
            if await submit_button.count() > 0:
                if not await submit_button.is_disabled():
                    print("[seven_rooms_submit] Clicking submit button...")
                    await submit_button.click()
                    await page.wait_for_timeout(5000)  # Wait for submission to process
                    
                    success_msg = "✅ Reservation submitted successfully"
                    print(f"[seven_rooms_submit] {success_msg}")
                    return ActionResult(extracted_content=success_msg)
                else:
                    error_msg = "❌ Submit button is disabled"
                    print(f"[seven_rooms_submit] {error_msg}")
                    return ActionResult(extracted_content=error_msg)
            else:
                error_msg = "❌ Submit button not found"
                print(f"[seven_rooms_submit] {error_msg}")
                return ActionResult(extracted_content=error_msg)
                
        except Exception as e:
            error_msg = f"❌ Error submitting reservation: {str(e)}"
            print(f"[seven_rooms_submit] {error_msg}")
            return ActionResult(extracted_content=error_msg)
    
    async def check_reservation_confirmation(self, page) -> ActionResult:
        """
        Check if the reservation was confirmed successfully.
        """
        try:
            print("[seven_rooms_confirmation] Checking reservation confirmation...")
            
            # Check for confirmation page
            confirmation_text = page.locator('text="We look forward to welcoming you."')
            if await confirmation_text.count() > 0:
                success_msg = "✅ Reservation confirmed successfully"
                print(f"[seven_rooms_confirmation] {success_msg}")
                return ActionResult(extracted_content=success_msg)
            else:
                # Check if there are any error messages
                error_messages = page.locator('[role="alert"], .error, .alert')
                if await error_messages.count() > 0:
                    parent_modal = error_messages.first.locator('xpath=..')
                    error_text = await parent_modal.inner_text()
                    error_msg = f"❌ Reservation failed: {error_text}"
                    error_msg = build_reservation_failure_message(error_text)
                    print(f"[seven_rooms_confirmation] {error_msg}")
                    return ActionResult(extracted_content=error_msg)
                else:
                    warning_msg = "⚠️ Reservation submitted but confirmation not found"
                    print(f"[seven_rooms_confirmation] {warning_msg}")
                    return ActionResult(extracted_content=warning_msg)
                    
        except Exception as e:
            error_msg = f"❌ Error checking confirmation: {str(e)}"
            print(f"[seven_rooms_confirmation] {error_msg}")
            return ActionResult(extracted_content=error_msg)
    
    async def close_popup_by_selector(self, page, selector: str | None = None) -> ActionResult:
        """
        Close popups that may appear during the reservation process.
        """
        try:
            print("[seven_rooms_popup] Checking for popups to close...")
            
            # Use provided selector or default to common close buttons
            if selector is not None:
                close_selectors = [selector]
            else:
                close_selectors = [
                    '[aria-label="Close"]',
                    '[data-test="close-button"]',
                    'button:has-text("×")',
                    'button:has-text("Close")',
                    '[aria-label*="close" i]'
                ]
            
            for close_selector in close_selectors:
                close_button = page.locator(close_selector)
                if await close_button.count() > 0:
                    try:
                        await close_button.click()
                        print(f"[seven_rooms_popup] Closed popup with selector: {close_selector}")
                        await page.wait_for_timeout(500)
                    except Exception:
                        continue
            
            success_msg = "ℹ️ Popup handling completed"
            print(f"[seven_rooms_popup] {success_msg}")
            return ActionResult(extracted_content=success_msg)
            
        except Exception as e:
            error_msg = f"❌ Error closing popups: {str(e)}"
            print(f"[seven_rooms_popup] {error_msg}")
            return ActionResult(extracted_content=error_msg)

    async def handle_login(self, page) -> ActionResult:
        """
        Handle login for SevenRooms.

        if not already logged in, there is guest login method, so we just need to click on it and here is the selector:
            - 1. ✅ Guest Login: button[data-test="sr-login-button-guest"]
        """
        try:
            print("[seven_rooms_login] Handling login...")

            await page.wait_for_selector('button[data-test="sr-login-button-guest"]', timeout=5000)

            # Check if we're already logged in
            if await page.locator('button[data-test="sr-login-button-guest"]').count() > 0:
                print("[seven_rooms_login] Not logged in, clicking guest login...")
                await page.locator('button[data-test="sr-login-button-guest"]').click()
                await page.wait_for_timeout(2000)
                return ActionResult(extracted_content="✅ Guest login successful")
            else:
                print("[seven_rooms_login] Already logged in")
                return ActionResult(extracted_content="✅ Already logged in")
                
        except Exception as e:
            error_msg = f"❌ Error handling login: {str(e)}"
            print(f"[seven_rooms_login] {error_msg}")
            return ActionResult(extracted_content=error_msg)
                  
    async def interact_with_error_modal(self, page) -> ActionResult:
        """
        Interact with the error modal for SevenRooms.
        """
        #  leave it for now
        return ActionResult(extracted_content="ℹ️ No error modal found for SevenRooms")
                
    async def focus_on_reservation_tab(self, browser_session) -> ActionResult:
        """
        Focus on the reservation tab and close unnecessary tabs for SevenRooms.
        """
        try:
            print("[seven_rooms_tab_focus] Focusing on SevenRooms reservation tab...")
            
            if not browser_session.browser_context:
                error_msg = "❌ No browser context found"
                print(f"[seven_rooms_tab_focus] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            target_tab = None
            pages = browser_session.browser_context.pages
            
            for page in pages:
                url = page.url
                print(f"[seven_rooms_tab_focus] Checking tab: {url}")
                if self.is_valid_url(url):
                    target_tab = page
                else:
                    print(f"[seven_rooms_tab_focus] Closing non-SevenRooms tab: {url}")
                    await page.close()
            
            if target_tab:
                await target_tab.bring_to_front()
                success_msg = f"✅ SevenRooms reservation tab focused: {target_tab.url}"
                print(f"[seven_rooms_tab_focus] {success_msg}")
                return ActionResult(extracted_content=success_msg)
            else:
                error_msg = "❌ No SevenRooms reservation tab found"
                print(f"[seven_rooms_tab_focus] {error_msg}")
                return ActionResult(extracted_content=error_msg)
                
        except Exception as e:
            error_msg = f"❌ Error focusing on reservation tab: {str(e)}"
            print(f"[seven_rooms_tab_focus] {error_msg}")
            return ActionResult(extracted_content=error_msg)
    
    async def reserve_with_provider(self, page, party_size: int, date: str, time_24h: str,
                                  first_name: str, last_name: str, phone: str, email: str) -> ActionResult:
        """
        Complete reservation flow for this provider.
        This is the main method that orchestrates the entire reservation process.
        """
        try:
            print(f"[seven_rooms_reservation] Starting full reservation flow...")
            
            # Step 1: Check if we're on the correct page
            if not page or not self.is_valid_url(page.url):
                error_msg = f"❌ Wrong page, please make sure it's {self.provider_name} reservation page with prefix: {self.url_prefix}"
                print(f"[seven_rooms_reservation] {error_msg}")
                return ActionResult(extracted_content=error_msg)
   
            # Close any popups
            await self.close_popup_by_selector(page=page, selector='[aria-label="Close"]')
            
            # Step 2: Select party size
            party_result = await self.select_reservation_party_size(page=page, party_size=party_size)
            if party_result.extracted_content and not party_result.extracted_content.startswith("✅"):
                return party_result
            
            await page.wait_for_timeout(1000)
            
            # Step 3: Select date
            date_result = await self.select_reservation_date(page=page, date=date)
            if date_result.extracted_content and not date_result.extracted_content.startswith("✅"):
                return date_result
            
            await page.wait_for_timeout(1000)
            
            # Step 4: Select time
            time_result = await self.select_reservation_time(page=page, desired_time=time_24h)
            if time_result.extracted_content and not time_result.extracted_content.startswith("✅"):
                return time_result
            
            await page.wait_for_timeout(2000)
            
            # Step 5: Click search button
            search_button = page.locator('button[data-test="sr-search-button"]')
            if await search_button.count() > 0:
                if not await search_button.is_disabled():
                    print("[seven_rooms_reservation] Clicking search button...")
                    await search_button.click()
                    await page.wait_for_timeout(3000)  # Wait for search results
                else:
                    error_msg = "❌ Search button is disabled"
                    print(f"[seven_rooms_reservation] {error_msg}")
                    return ActionResult(extracted_content=error_msg)
            else:
                error_msg = "❌ Search button not found"
                print(f"[seven_rooms_reservation] {error_msg}")
                return ActionResult(extracted_content=error_msg)
            
            # Step 6: Handle search results
            
            time_slot_result = await self.select_from_available_time_slots(page=page, desired_time=time_24h)
            if time_slot_result.extracted_content and not time_slot_result.extracted_content.startswith("✅"):
                return time_slot_result
            
            await page.wait_for_timeout(2000)
            
            # Step 8: Handle provider-specific popups
            provider_result = await self.select_reservation_provider(page=page)
            if (provider_result.extracted_content and 
                not provider_result.extracted_content.startswith("✅") and 
                not provider_result.extracted_content.startswith("ℹ️")):
                return provider_result
            
            await page.wait_for_timeout(1000)

            # Step 8.5: Handle login
            login_result = await self.handle_login(page=page)
            if login_result.extracted_content and login_result.extracted_content.startswith("✅"):
                print("[seven_rooms_reservation] logged in")
            else:
                print("[seven_rooms_reservation] Error logging in")
            
            await page.wait_for_timeout(1000)
            
            # Step 9: Update contact information
            contact_result = await self.update_reservation_contact_info(
                page=page, first_name=first_name, last_name=last_name, phone=phone, email=email
            )
            if contact_result.extracted_content and not contact_result.extracted_content.startswith("✅"):
                return contact_result
            
            await page.wait_for_timeout(2000)
            
            # Step 10: Finalize the booking
            finalize_result = await self.finalize_booking(page)
            if finalize_result.extracted_content and not finalize_result.extracted_content.startswith("✅"):
                return finalize_result
            
            await page.wait_for_timeout(2000)
            
            # Success message
            success_msg = build_reservation_success_message(RESERVATION_SUCCESSES["reservation_complete"].format(party_size=party_size, date=date, time_24h=time_24h))
            print(f"[seven_rooms_reservation] {success_msg}")
            return ActionResult(extracted_content=success_msg, success=True, is_done=True)
            
        except Exception as e:
            error_msg = f"❌ Error in reservation flow: {str(e)}"
            print(f"[seven_rooms_reservation] {error_msg}")
            return ActionResult(extracted_content=error_msg)
    