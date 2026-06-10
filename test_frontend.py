import asyncio
from playwright.async_api import async_playwright
import subprocess
import time

async def test_search():
    # Start backend
    backend = subprocess.Popen(["uvicorn", "api.index:app", "--port", "8000"])

    # Start frontend
    frontend = subprocess.Popen(["python3", "-m", "http.server", "8001"])

    # Wait for servers to start
    time.sleep(3)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Listen for console events
            page.on("console", lambda msg: print(f"Browser console: {msg.type}: {msg.text}"))
            page.on("pageerror", lambda err: print(f"Browser error: {err.message}"))

            # Route API requests to backend
            async def route_handler(route):
                request = route.request
                url = request.url
                if "/api/" in url:
                    new_url = url.replace("http://localhost:8001/api/", "http://localhost:8000/api/")
                    print(f"Routing {url} -> {new_url}")
                    try:
                        response = await page.request.fetch(
                            new_url,
                            method=request.method,
                            headers=request.headers,
                            data=request.post_data,
                            timeout=60000 # 60 seconds for long backend processes
                        )
                        await route.fulfill(
                            status=response.status,
                            headers=response.headers,
                            body=await response.body()
                        )
                    except Exception as e:
                        print(f"Route error: {e}")
                        await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", route_handler)

            print("Navigating to frontend...")
            await page.goto("http://localhost:8001")

            # Make sure page is loaded
            await page.wait_for_selector("#ticker-input", timeout=10000)

            print("Entering search query...")
            await page.fill("#ticker-input", "AAPL")
            await page.click("#search-btn")

            print("Waiting for search to complete...")
            try:
                await page.wait_for_selector("#ownership-section", state="visible", timeout=60000)
                await page.wait_for_timeout(3000) # extra buffer for animations
            except Exception as e:
                print(f"Timeout waiting for rendering: {e}")

            await page.screenshot(path="frontend_test.png", full_page=True)
            print("Screenshot saved to frontend_test.png")

            await browser.close()

    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        # Cleanup
        backend.terminate()
        frontend.terminate()

asyncio.run(test_search())
