import asyncio
import requests
import json


def build_time_prompt(task):
    return f"""
    Checking Task:
    - URL: {task["restaurant_url"]}
    - Date: {task["date"]}
    - Time: {task["time"]}

    Your task is to check if the time {task["time"]} is available. That's all your task just checking if the time is available.

    In order to do this follow the steps below accordingly:

    1. Open the url
   - Use the `select_reservation_time` tool by passing the requested time in 24-hour format (e.g., "13:30").
   - The tool will select the time and confirm if the time is available based on whether the Continue button is enabled.
   - ❌ If the time is not available, return: "Time {task["time"]} not available."
   - ✅ If available, return with success message

   IMPORTANT:
   - Always use the link on reserve a table button. do not go to site like:
      - Zomato, opentable, or any other than reserve with google which is found on reserve a table button
    """


def build_prompt(task):
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

def build_prompt_date(task):
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

3. Then check if the **requested date** is available.
   - Use the `select_reservation_date` tool by passing the requested date in YYYY-MM-DD format.
   - The tool will select the date and confirm if the date is available.
   - ❌ If the date is not available, return: "Date {task["date"]} not available."
   - ✅ If available, proceed to the next step.

4. Then check if the **requested time** is available.
   - Use the `select_reservation_time` tool by passing the requested time in 24-hour format (e.g., "13:30").
   - The tool will select the time and confirm if the time is available based on whether the Continue button is enabled.
   - ❌ If the time is not available, return: "Time {task["time"]} not available."
   - ✅ If available, proceed with the selection.

5. Then check if the **requested party size** is available.
   - Use the `select_reservation_party_size` tool by passing the requested party size in number format.
   - The tool will select the party size and confirm if the party size is available.
   - ❌ If the party size is not available, return: "Party size {task["party_size"]} not available."
   - ✅ If available, Proceed.


6. Once all fields are selected and verified:
   - ✅ Click “Continue”.
   - ✅ Click “Book”. You will need to scroll down to see the book button.
   - 🖼️ cheeck the confirmation page.

7. Return success if booking is confirmed, or the failure reason if not.


⛔ Important Notes:
- Never assume an input is valid — always verify availability using your tools.
- Always respond early if the date is unavailable. Do not check party size or time before that.
"""


def build_manual_prompt(task):
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

3. Make a call to 'make_reservation' tool with appropriate paramters. which are page: Page, party_size: int, date: str, time_24h: str.

4. stop and return what ever is returned from the make_reservation tool

   """

async def run_tests():
    success_test_cases = "test/test_data/success_test_cases.json"
    failure_test_cases = "test/failure_test_cases.json" 
    with open(success_test_cases, "r") as f:
        test_cases = json.load(f)

    results = []

    for idx, task in enumerate(test_cases):
        # prompt = build_prompt(task)
        prompt = build_prompt_date(task)

        # API_BASE_URL = "http://browser-use.northeurope.cloudapp.azure.com"
        API_BASE_URL = "http://localhost:8000"

        try:
            response = requests.post(
                f"{API_BASE_URL}/api/v1/book",
                json={"task": prompt}
            )
            response.raise_for_status()
            task_id = response.json()["session_id"]
            print(
                f"✅ Test {idx + 1}: Task created successfully with ID: {task_id}")

            # Store the result
            results.append({
                "task_id": task_id,
                "task_details": task,
                "expected_result": task["expected"]
            })

        except Exception as e:
            print(f"❌ Test {idx + 1} failed to submit: {e}")
            results.append({
                "task_id": None,
                "task_details": task,
                "expected_result": task["expected"],
                "error": str(e)
            })
        break

    with open("test_results.json", "w") as f:
        json.dump(results, f, indent=4)

    print("📁 All test results saved to test_results.json")

if __name__ == "__main__":
    asyncio.run(run_tests())
