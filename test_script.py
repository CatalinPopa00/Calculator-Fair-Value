from playwright.sync_api import sync_playwright
import time

def verify_button(page):
    # Mocking endpoints to prevent actual fetching
    page.route('**/api/search?*', lambda route: route.fulfill(status=200, json=[{"symbol":"AAPL","name":"Apple"}]))
    page.route('**/api/valuation/*', lambda route: route.fulfill(status=200, json={}))

    # Go to app
    page.goto('http://localhost:8000')

    # Take screenshot of app loading
    time.sleep(1)
    page.screenshot(path='/home/jules/verification/1_initial.png')

    # Open Search Modal
    trigger = page.locator('#bnav-search')
    trigger.evaluate("node => node.click()")
    time.sleep(1)

    page.screenshot(path='/home/jules/verification/2_search_modal.png')

    # Enter query
    page.fill('#ticker-input', 'AAPL')
    time.sleep(1)
    page.screenshot(path='/home/jules/verification/3_search_input.png')

    # Wait for the button
    btn = page.locator('#search-btn')
    btn.evaluate("node => node.click()")

    # Wait for processing state to settle (spinning icon)
    time.sleep(0.5)
    page.screenshot(path='/home/jules/verification/4_processing.png')

    # Wait for success state to settle (check icon)
    time.sleep(1.5)
    page.screenshot(path='/home/jules/verification/5_success.png')
    print("Screenshots taken")


if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            verify_button(page)
        finally:
            browser.close()
