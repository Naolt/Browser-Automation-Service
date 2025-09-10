import asyncio
from playwright.async_api import async_playwright
from services.actions.provider.open_table_provider import OpenTableProvider

async def main():
    provider = OpenTableProvider()
    time = "23:00"  # Use a size that triggers the error (adjust as needed)
    url = "https://www.opentable.ae/r/filia-dubai?ref=18584"  # Example restaurant

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--window-size=1280,900"])  # headful mode with window size
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()
        await page.goto(url)

        # Wait for the page to load (adjust selector as needed)
        # await page.wait_for_selector('[data-test="party-size-picker"]')

        # Call your provider method
        result = await provider.select_reservation_time(page, time)
        print("Result:", result.extracted_content)

        # keep the browser open for a bit to observe
        # await asyncio.sleep(1000000)
        # Keep the browser open for a bit to observe
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())