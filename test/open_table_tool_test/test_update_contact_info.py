import pytest
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

@pytest.mark.asyncio
async def test_update_contact_info_success():
    provider = OpenTableProvider()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(SUCCESS_URL)
        await page.wait_for_timeout(2000)

        result = await provider.update_reservation_contact_info(
            page, FIRST_NAME, LAST_NAME, PHONE, EMAIL
        )
        print("Contact info (success) result:", result.extracted_content)
        assert "success" in result.extracted_content.lower()
        await browser.close()

@pytest.mark.asyncio
async def test_update_contact_info_credit_card_required():
    provider = OpenTableProvider()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(FAILURE_URL)
        await page.wait_for_timeout(2000)

        result = await provider.update_reservation_contact_info(
            page, FIRST_NAME, LAST_NAME, PHONE, EMAIL
        )
        print("Contact info (credit card required) result:", result.extracted_content)
        assert "fatal" in result.extracted_content.lower()
        await browser.close() 