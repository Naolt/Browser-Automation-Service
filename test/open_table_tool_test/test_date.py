import asyncio
import pytest
from playwright.async_api import async_playwright
from services.actions.provider.open_table_provider import OpenTableProvider
import logging
logging.basicConfig(level=logging.INFO)

RESTAURANT_URL = "https://www.opentable.ae/r/filia-dubai?ref=18584"
WAIT_TIME = 3000



@pytest.mark.asyncio
async def test_available_date():
    provider = OpenTableProvider()
    url = RESTAURANT_URL
    date = "2025-07-22" 

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(WAIT_TIME)
        result = await provider.select_reservation_date(page, date)
        assert "✅" in result.extracted_content
        await browser.close()

@pytest.mark.asyncio
async def test_unavailable_date():
    provider = OpenTableProvider()
    url = RESTAURANT_URL
    date = "2025-07-14"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(WAIT_TIME)
        result = await provider.select_reservation_date(page, date)
        assert "❌" in result.extracted_content
        await browser.close()

@pytest.mark.asyncio
async def test_invalid_date():
    provider = OpenTableProvider()
    url = RESTAURANT_URL
    date = "2025-07" 

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(WAIT_TIME)
        result = await provider.select_reservation_date(page, date)
        assert "❌" in result.extracted_content
        await browser.close()