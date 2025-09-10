import asyncio
import pytest
from playwright.async_api import async_playwright
from services.actions.provider.open_table_provider import OpenTableProvider
import logging
logging.basicConfig(level=logging.INFO)

RESTAURANT_URL = "https://www.opentable.ae/r/filia-dubai?ref=18584"
WAIT_TIME = 3000



@pytest.mark.asyncio
async def test_available_time():
    provider = OpenTableProvider()
    url = RESTAURANT_URL
    time = "18:00" 

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(WAIT_TIME)
        result = await provider.select_reservation_time(page, time)
        assert "✅" in result.extracted_content
        await browser.close()

@pytest.mark.asyncio
async def test_available_time_with_approx_time():
    provider = OpenTableProvider()
    url = RESTAURANT_URL
    time = "19:05"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(WAIT_TIME)
        result = await provider.select_reservation_time(page, time)
        assert "✅" in result.extracted_content
        await browser.close()
    
    

@pytest.mark.asyncio
async def test_unavailable_time():
    provider = OpenTableProvider()
    url = RESTAURANT_URL
    time = "19:05"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(WAIT_TIME)
        result = await provider.select_reservation_time(page, time)
        assert "❌" in result.extracted_content
        await browser.close()

@pytest.mark.asyncio
async def test_invalid_time():
    provider = OpenTableProvider()
    url = RESTAURANT_URL
    time = "2025-07" 

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_timeout(WAIT_TIME)
        result = await provider.select_reservation_time(page, time)
        assert "❌" in result.extracted_content
        await browser.close()