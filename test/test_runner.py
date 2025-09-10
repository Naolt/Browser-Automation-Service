# tests/test_runner.py
import json
import requests
import asyncio # Keep if your API calls are truly async, or remove if using synchronous 'requests'
import os

RESERVATION_URL_PREFIX = "https://www.google.com/maps/reserve"

class TestRunner:
    def __init__(self, api_base_url):
        self.api_base_url = api_base_url

    def _load_test_cases(self, file_path):
        """Helper to load test cases from a given JSON file."""
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Test case file not found at {file_path}")
            return []
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {file_path}")
            return []

    def _build_prompt(self, task):
        return f"""
You are an assistant using a browser to make reservations via Reserve with Google.

Reservation Task:
- Restaurant: {task["restaurant_name"]}
- URL: {task["restaurant_url"]}
- Party Size: {task["party_size"]}
- Date: {task["date"]}
- Time: {task["time"]}

## Instructions:

1. Visit the restaurant URL.


2. Look for the "Reserve a table" option (Reserve with Google).
   - ✅ If available, click on it and proceed.
   - ❌ If not available, try 3 more time and then return: "Reservation system not available" and stop.

3. Open the **calendar widget** and check if the target date is available: Use the steps below
   - First click on the calendar input.
   - Check if the calendar widget is opened
   - If it is opened, navigate to the desired month.
   - 🛠️ Use the `get_available_dates` tool to get list of available dates for the selected month. Before calling this tool navigate to the desired month then call the tool.
   - 🔍 The tool will return with list of dates that are available for that month. if returns empty array it means there are non available that month
     - ❌ If the requested date is not in the list returned, return: "Requested date {task["date"]} is unavailable."
     - ✅ If available, click on the requested date.
         - Verify if the date is clicked
     - The key thing you must not forget is before trying to click dates you first need to call get_available_dates tool. we are doing this because if you click on a date that is not available it will close the calendar widget as if it set the value but in reality it just closed the calendar widget it didn't change the value of the input. so this is a tool made to solve this problem.

⚠️ You must always **verify the date is available first** using `get_available_dates`. Do not proceed to party size or time until date is selected.

4. After a valid date is confirmed:
   - Check if the **party size** is listed in the dropdown.
     - ❌ If not available, return: "Party size {task["party_size"]} not available."
   - ✅ If available, select it and verify the selection.

5. Then check if the **requested time** is available.
   - Use the `select_reservation_time` tool by passing the requested time in 24-hour format (e.g., "13:30").
   - The tool will select the time and confirm if the time is available based on whether the Continue button is enabled.
   - ❌ If the time is not available, return: "Time {task["time"]} not available."
   - ✅ If available, proceed with the selection.


6. Once all fields are selected and verified:
   - ✅ Click “Continue”.
   - ✅ Verify that all reservation details match with the users request.
   - ✅ Click “Book”. You will need to scroll down to see the book button.
   - 🖼️ cheeck the confirmation page.

7. Return success if booking is confirmed, or the failure reason if not.


⛔ Important Notes:
- Never assume an input is valid — always verify availability using your tools.
- Always respond early if the date is unavailable. Do not check party size or time before that.
"""

    def _build_prompt_v2(self, task):
        return f"""
You are an assistant using a browser to make reservations via Reserve with Google.

Reservation Task:
- Restaurant: {task["restaurant_name"]}
- URL: {task["restaurant_url"]}
- Party Size: {task["party_size"]}
- Date: {task["date"]}
- Time: {task["time"]}
User Information:
- First Name: Hana
- Last Name: Tesfaye
- Email: hana.tesfaye@gmail.com
- Phone Number: +251 91 234 5678



## Instructions:

1. Visit the restaurant URL.


2. Look for the "Reserve a table" option (Reserve with Google).
   - ✅ If available, click on it and proceed.
   - ❌ If not available, try 3 more time and then return: "Reservation system not available" and stop.

3. Close the other tabs. make sure the only remaining tab is with prefix: {RESERVATION_URL_PREFIX}

4. Then check if the **requested party size** is available.
- Use the `select_reservation_party_size` tool by passing the requested party size in number format.
- The tool will select the party size and confirm if the party size is available.
- ❌ If the party size is not available, return: "Party size {task["party_size"]} not available."
- ✅ If available, Proceed.

5. Then check if the **requested date** is available.
   - Use the `select_reservation_date` tool by passing the requested date in YYYY-MM-DD format.
   - The tool will select the date and confirm if the date is available.
   - ❌ If the date is not available, return: "Date {task["date"]} not available."
   - ✅ If available, proceed to the next step.

6. Then check if the **requested time** is available.
   - Use the `select_reservation_time` tool by passing the requested time in 24-hour format (e.g., "13:30").
   - The tool will select the time and confirm if the time is available based on whether the Continue button is enabled.
   - ❌ If the time is not available, return: "Time {task["time"]} not available."
   - ✅ If available, proceed with the Clicking Continue.

7. Click “Continue”. 
8. Update the user information
8. Click “Book”. You will need to scroll down to see the book button.
9. check the confirmation page.
10. Return success if booking is confirmed, or the failure reason if not.


⛔ Important Notes:
- Never assume an input is valid — always verify availability using your tools.
- Always respond early if the date is unavailable. Do not check party size or time before that.
"""
    def _build_prompt_v3(self, task):
        return f"""
You are an assistant using a browser to make reservations. You have make_reservation_smart tool to make reservations..

Reservation Task:
- Restaurant: {task["restaurant_name"]}
- URL: {task["restaurant_url"]}
- Party Size: {task["party_size"]}
- Date: {task["date"]}
- Time: {task["time"]}

Contact Information:
- First Name: Selay
- Last Name: Bokolo
- Phone Number: +251911374567
- Email: selay.bokolo@example.com

## Instructions:

1. Visit the URL provided. 

2. Call the `make_reservation_smart` tool  IMMEDIATELY with the following inputs: restaurant_google_maps_url({task["restaurant_url"]}), date, time, party size, and contact details (first name, last name, phone, and email).

   - The tool will handle all necessary interactions, including selecting the appropriate provider, opening the page, selecting the party size, date, time, and inputting contact information, and booking the reservation.
   
3. `make_reservation_smart` Tool Response Handling:

   - ✅ If the tool returns a message starting with "✅" or [Success], assume the reservation was successful.  
     - Return: `"✅ Reservation successful"` along with the reservation details.
     - Do not proceed further.

   - ❌ If the response starts with `[FATAL]`:
     - This indicates a **terminal failure** (e.g., time not available, date not available, party size not available, etc.).
     - ⛔ You must immediately stop execution.
     - 🔁 Do **not** retry or attempt alternative booking strategies.
     - 🔄 Do **not** invoke any other tools.
     - 📤 Return the tool’s message **exactly as received** to the user.

   - ⚠️ For any other errors that doesn't start with `[FATAL]`:
     - These are considered recoverable failures or tool limitations.
     - ✅ You are allowed to help the reservation process using your own capabilities.
     - Proceed cautiously by attempting to book manually on the page using known good selectors and flows.
     - You may retry the booking flow at most **once**.`

"""

    # This is where your original `run_tests` logic goes, adapted for the class
    async def _run_and_save(self, test_cases_path, output_path, test_type_name=""):
        """
        Generic helper to run tests from a given path and save results.
        """
        print(f"\n--- Running {test_type_name.capitalize()} Tests ---")
        test_cases = self._load_test_cases(test_cases_path)
        # start,end = 0,len(test_cases)
        start,end = 2,3

        if not test_cases:
            print(f"No {test_type_name} test cases loaded from {test_cases_path}. Skipping.")
            return

        results = []
        for idx in range(start, end):
            task = test_cases[idx]
            prompt = self._build_prompt_v3(task)
            print(f"Running {test_type_name.capitalize()} Test {idx + 1}/{len(test_cases)}: "
                  f"{task.get('restaurant_name')} - {task.get('date')} {task.get('time')} "
                  f"(Expected: {task.get('expected')})")

            try:
                response = requests.post(
                    f"{self.api_base_url}/api/v1/book",
                    json={"task": prompt}
                )
                response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
                task_id = response.json()["session_id"]
                print(f"✅ Test {idx + 1}: Task created successfully with ID: {task_id}")

                results.append({
                    "task_id": task_id,
                    "task_details": task,
                    "expected_result": task["expected"]
                })

            except requests.exceptions.RequestException as e:
                print(f"❌ Test {idx + 1} failed to submit (API request error): {e}")
                results.append({
                    "task_id": None,
                    "task_details": task,
                    "expected_result": task["expected"],
                    "error": str(e)
                })
            except Exception as e:
                print(f"❌ Test {idx + 1} failed due to unexpected error: {e}")
                results.append({
                    "task_id": None,
                    "task_details": task,
                    "expected_result": task["expected"],
                    "error": str(e)
                })

        self._save_results(results, output_path)
        print(f"📁 All raw {test_type_name} test results saved to {output_path}")

    async def run_success_tests(self, success_cases_path, output_path):
        """Runs only the success test cases."""
        await self._run_and_save(success_cases_path, output_path, "success")

    async def run_failure_tests(self, failure_cases_path, output_path):
        """Runs only the failure test cases."""
        await self._run_and_save(failure_cases_path, output_path, "failure")

    def _save_results(self, results, output_path):
        """Helper to save results to a specified JSON file."""
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=4)
