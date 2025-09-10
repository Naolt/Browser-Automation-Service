import asyncio
import pytest
from playwright.async_api import async_playwright
from services.actions.provider.open_table_provider import OpenTableProvider
import logging
logging.basicConfig(level=logging.INFO)

RESTAURANT_URL = "https://www.opentable.ae/r/filia-dubai?ref=18584"
WAIT_TIME = 3000

@pytest.mark.asyncio
async def test_party_size_too_large():
    provider = OpenTableProvider()
    url = RESTAURANT_URL
    party_size = 20  # Should trigger 'too large' error

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(WAIT_TIME)
        result = await provider.select_reservation_party_size(page, party_size)
        assert "too large to book online" in result.extracted_content.lower()
        await browser.close()

@pytest.mark.asyncio
async def test_valid_party_size():
    provider = OpenTableProvider()
    url = RESTAURANT_URL
    party_size = 2  # Should be available

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(WAIT_TIME)
        print(f"Page URL: {page.url}")
        print(f"Provider: {provider.provider_name}")
        result = await provider.select_reservation_party_size(page, party_size)
        assert "✅" in result.extracted_content
        await browser.close()

@pytest.mark.asyncio
async def test_party_size_not_available():
    provider = OpenTableProvider()
    url = RESTAURANT_URL
    party_size = 99  # Should not be available

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(WAIT_TIME)
        result = await provider.select_reservation_party_size(page, party_size)
        assert "party size not available" in result.extracted_content.lower()
        await browser.close()


@pytest.mark.asyncio
async def test_invalid_page():
    provider = OpenTableProvider()
    url = "https://www.sevenrooms.com"
    party_size = 2

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        result = await provider.select_reservation_party_size(page, party_size)
        assert "wrong page" in result.extracted_content.lower()
        await browser.close()