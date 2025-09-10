import asyncio
from playwright.async_api import async_playwright
from services.actions.provider.google_provider import GoogleProvider
from services.reservation_service import ReservationService
from services.actions.provider.open_table_provider import OpenTableProvider
from services.actions.provider.seven_rooms_provider import SevenRoomsProvider

# Connect to the first Chrome profile launched by launch_chrome_profiles.py
BROWSER_WS_ENDPOINT = "http://localhost:9222"


async def main():
    # Create reservation service with providers
    service = ReservationService([
        OpenTableProvider(),
        SevenRoomsProvider(),
        GoogleProvider(),
    ])
    
    # Sample reservation data
    url_open_table = "https://www.google.com/maps/place/Doors+Freestyle+Grill+-+Steakhouse/@25.2297876,55.13523,11z/data=!4m6!3m5!1s0x3e5f4398d2ebc55b:0xe2910fdaf0fe93f!8m2!3d25.2568757!4d55.3120811!16s%2Fg%2F11gh9nyzl_?entry=ttu&g_ep=EgoyMDI1MDcyMC4wIKXMDSoASAFQAw%3D%3D&hl=en"  # Example restaurant
    url_seven_rooms = "https://www.google.com/maps/place/RSVP+Restaurant/@25.2026039,55.2485025,17z/data=!3m1!4b1!4m14!1m7!3m6!1s0x3e5f4398d2ebc55b:0xe2910fdaf0fe93f!2sDoors+Freestyle+Grill+-+Steakhouse!8m2!3d25.2568757!4d55.3120811!16s%2Fg%2F11gh9nyzl_!3m5!1s0x3e5f430086d25ab3:0xabd49eaf3f50ea19!8m2!3d25.2025991!4d55.2510774!16s%2Fg%2F11t4_j2jx9?entry=ttu&g_ep=EgoyMDI1MDcyMC4wIKXMDSoASAFQAw%3D%3D&hl=en"
    url_google = "https://www.google.com/maps/place/Sheger+Restaurant/@24.4898787,54.380424,17z/data=!3m1!4b1!4m14!1m7!3m6!1s0x3e5f4398d2ebc55b:0xe2910fdaf0fe93f!2sDoors+Freestyle+Grill+-+Steakhouse!8m2!3d25.2568757!4d55.3120811!16s%2Fg%2F11gh9nyzl_!3m5!1s0x3e5e664ef6eb137d:0x6d38a52b93d7940a!8m2!3d24.4898738!4d54.3829989!16s%2Fg%2F11dyx8r3x7?hl=en&entry=ttu&g_ep=EgoyMDI1MDcyMC4wIKXMDSoASAFQAw%3D%3D&hl=en"
    url_google_2 = "https://www.google.com/maps/place/Doors+Freestyle+Grill+-+Steakhouse/@25.2568757,55.3120811,17z/data=!3m1!4b1!4m6!3m5!1s0x3e5f4398d2ebc55b:0xe2910fdaf0fe93f!8m2!3d25.2568757!4d55.3120811!16s%2Fg%2F11gh9nyzl_?entry=ttu&g_ep=EgoyMDI1MDcyMC4wIKXMDSoASAFQAw%3D%3D&hl=en"
    party_size = 4
    date = "2025-07-27"  # YYYY-MM-DD
    time_24h = "19:00"    # HH:MM
    first_name = "Test"
    last_name = "User"
    phone = "+971501234567"
    email = "test.user@example.com"

    async with async_playwright() as p:
         # Connect to the running Chrome instance via CDP
        browser = await p.chromium.connect_over_cdp(BROWSER_WS_ENDPOINT)
        default_context = browser.contexts[0]
        page = default_context.pages[0]
        await page.goto(url_seven_rooms)
        # await page.goto(url_google_2)

        # Wait for the page to load
        await page.wait_for_timeout(2000)

        # Call the reservation service
        result = await service.make_reservation(
            page, party_size, date, time_24h, 
            first_name, last_name, phone, email
        )
        
        print("Reservation service result:", result.extracted_content)

        # Keep the browser open for a bit to observe
        await asyncio.sleep(5)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main()) 