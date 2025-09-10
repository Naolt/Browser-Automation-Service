import pytest
from playwright.async_api import async_playwright
from services.actions.provider.open_table_provider import OpenTableProvider

# Replace this with a real OpenTable seating options URL for your test case
SEATING_OPTIONS_URL = "https://www.opentable.ae/booking/seating-options?availabilityToken=eyJ2IjoyLCJtIjoxLCJwIjowLCJjIjo1NzY2NTU2LCJzIjoxLCJuIjowfQ&correlationId=64158d39-2c29-4f10-a150-8b53120fca19&creditCardRequired=false&dateTime=2025-07-22T19:00:00&experienceIds=509865,476633&partySize=2&points=100&pointsType=Standard&resoAttribute=default&rid=1422478&slotHash=2414404218&isModify=false&isMandatory=false&cfe=true&st=Experience"

@pytest.mark.asyncio
async def test_select_seating_option():
    provider = OpenTableProvider()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(SEATING_OPTIONS_URL)
        await page.wait_for_timeout(2000)

        result = await provider.select_seating_option(page)
        print("Seating option result:", result.extracted_content)
        assert "success" in result.extracted_content.lower()

        await browser.close() 


@pytest.mark.asyncio
async def test_select_seating_option_with_wrong_url():
    provider = OpenTableProvider()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://www.opentable.com")
        await page.wait_for_timeout(2000)

        result = await provider.select_seating_option(page)
        print("Seating option result:", result.extracted_content)
        assert "wrong" in result.extracted_content.lower()

        await browser.close() 