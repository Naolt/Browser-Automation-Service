import asyncio
from playwright.async_api import async_playwright
from services.actions.provider.open_table_provider import OpenTableProvider


# URLs for testing
SUCCESS_URL = "https://www.opentable.ae/booking/details?availabilityToken=eyJ2IjoyLCJtIjoxLCJwIjowLCJjIjo1NzY2NTU2LCJzIjoxLCJuIjowfQ&correlationId=64158d39-2c29-4f10-a150-8b53120fca19&creditCardRequired=false&dateTime=2025-07-22T19%3A00%3A00&experienceIds=509865%2C476633&partySize=2&points=100&pointsType=Standard&resoAttribute=default&rid=1422478&slotHash=2414404218&isModify=false&isMandatory=false&cfe=true&st=Experience&tableCategory=default&diningAreaId=1&selectedNonSpecialType=NONE"
FAILURE_URL = "https://www.opentable.ae/booking/details?availabilityToken=eyJ2IjoyLCJtIjoxLCJwIjowLCJjIjoxMDg3MjUxLCJzIjoxLCJuIjowfQ&correlationId=76f6e3b0-4e12-4cc3-b259-9e62dffbfba0&creditCardRequired=true&dateTime=2025-07-22T19%3A45%3A00&partySize=2&points=100&pointsType=Standard&resoAttribute=default&rid=1057525&slotHash=2660509994&isModify=false&isMandatory=false&cfe=true&st=Standard"

# Sample contact info
FIRST_NAME = "Test"
LAST_NAME = "User"
PHONE = "+971501234567"  # UAE sample
EMAIL = "test.user@example.com"



async def main():
    provider = OpenTableProvider()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--window-size=1280,900"])  # headful mode with window size
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()
        await page.goto(SUCCESS_URL)

        # Wait for the page to load (adjust selector as needed)
        # await page.wait_for_selector('[data-test="party-size-picker"]')

        # Call your provider method
        result = await provider.update_reservation_contact_info(page, FIRST_NAME, LAST_NAME, PHONE, EMAIL)
        print("Result:", result.extracted_content)

        # keep the browser open for a bit to observe
        # await asyncio.sleep(1000000)
        # Keep the browser open for a bit to observe
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())