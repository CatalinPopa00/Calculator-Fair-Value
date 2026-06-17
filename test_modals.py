from playwright.sync_api import sync_playwright
import time
import subprocess

def test_modal():
    print("Starting frontend...")
    frontend = subprocess.Popen(["python", "-m", "http.server", "8002"])

    time.sleep(3) # Wait for servers to start

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("http://localhost:8002")
        time.sleep(1) # wait for js to load

        # We don't need a full end-to-end load to test the HTML generation of the modal.
        # We can just open the page, inject some mock globalData, and trigger the modal rendering.

        page.evaluate("""
            window.globalData = {
                ticker: "AAPL",
                company_profile: {
                    market_cap: 3000000000000,
                    shares_outstanding: 15000000000,
                    fwd_pe: 28,
                    forward_ev_ebitda: 20
                },
                current_price: 180
            };
            window._currentScenario = 'base';
            window._scenarioFvData = {
                base: {
                    relative: {
                        mean_peer_pe: 25,
                        mean_peer_ev_ebitda: 18,
                        company_fwd_eps: 6.5,
                        peers: [
                            {ticker: "MSFT", pe_ratio: 30, ev_to_ebitda: 22},
                            {ticker: "GOOGL", pe_ratio: 22, ev_to_ebitda: 15}
                        ]
                    }
                }
            };

            // Create a mock modal element if it doesn't exist
            let modal = document.getElementById('calc-modal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'calc-modal';
                modal.style.display = 'none';
                document.body.appendChild(modal);

                const title = document.createElement('div');
                title.id = 'calc-modal-title';
                modal.appendChild(title);

                const body = document.createElement('div');
                body.id = 'calc-modal-body';
                modal.appendChild(body);
            }

            // Wait a little before calling showCalculationModal
        """)

        time.sleep(1)
        try:
            page.evaluate("window.showCalculationModal('relative')")

            # Check if the modal body has the correct font sizes
            modal_body_html = page.evaluate("document.getElementById('calc-modal-body').innerHTML")

            if "font-size:0.65rem" in modal_body_html:
                print("Successfully found updated font size 0.65rem in the generated HTML!")
            else:
                print("Failed to find updated font size 0.65rem in the generated HTML.")

            if "padding:2px" in modal_body_html:
                print("Successfully found updated padding 2px in the generated HTML!")
            else:
                print("Failed to find updated padding 2px in the generated HTML.")
        except Exception as e:
            print("Error calling JS function:", e)

        browser.close()

    frontend.terminate()

test_modal()
