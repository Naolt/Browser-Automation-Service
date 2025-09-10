import asyncio
from playwright.async_api import async_playwright
from services.actions.provider.open_table_provider import OpenTableProvider

async def main():
    provider = OpenTableProvider()
    date = "2025-07-22"  # Use a size that triggers the error (adjust as needed)
    url = "https://www.opentable.ae/r/filia-dubai?ref=18584"  # Example restaurant

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headful mode
        page = await browser.new_page()
        await page.goto(url)

        # Wait for the page to load (adjust selector as needed)
        # await page.wait_for_selector('[data-test="party-size-picker"]')

        # Call your provider method
        result = await provider.select_reservation_date(page, date)
        print("Result:", result.extracted_content)

        # Keep the browser open for a bit to observe
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())