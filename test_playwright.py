from playwright.sync_api import sync_playwright
import os


def test_playwright():
    # Set display for Xvfb
    os.environ['DISPLAY'] = ':99'

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto('https://example.com')
        print("Playwright is working! Successfully opened example.com")
        browser.close()


if __name__ == "__main__":
    test_playwright()
