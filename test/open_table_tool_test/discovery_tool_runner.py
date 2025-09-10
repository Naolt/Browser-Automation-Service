import asyncio
from playwright.async_api import async_playwright
from services.actions.discovery_service import ReservationDiscoveryService

async def main():
    url = "https://www.google.com/maps/place/Doors+Freestyle+Grill+-+Steakhouse/@25.2297876,55.13523,11z/data=!4m6!3m5!1s0x3e5f4398d2ebc55b:0xe2910fdaf0fe93f!8m2!3d25.2568757!4d55.3120811!16s%2Fg%2F11gh9nyzl_?entry=ttu&g_ep=EgoyMDI1MDcyMC4wIKXMDSoASAFQAw%3D%3D&hl=en"  # Example restaurant
    restaurant_name = "Filia Dubai"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url)

        # Wait for the page to load (adjust selector as needed)
        # await page.wait_for_selector('...')

        # Call the discovery method
        result = await ReservationDiscoveryService._find_find_table_options(page)
        print("Discovery result:", result)

        print("--------------------------------")
        print("--------------------------------")

        # print the available options:
        print(result)
        # Keep the browser open for a bit to observe
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 