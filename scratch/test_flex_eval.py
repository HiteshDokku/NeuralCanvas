import time

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8503")
    page.wait_for_selector(".st-key-nc-center")
    time.sleep(1)
    res = page.evaluate("""() => {
        const center = document.querySelector('.st-key-nc-center');
        const settings = document.querySelector('.st-key-nc-settings');
        const cols = document.querySelectorAll('[data-testid="stColumn"]');
        return {
            center: {
                clientWidth: center.clientWidth,
                clientHeight: center.clientHeight,
                scrollHeight: center.scrollHeight,
                overflowY: window.getComputedStyle(center).overflowY
            },
            settings: {
                clientWidth: settings.clientWidth,
                clientHeight: settings.clientHeight,
                scrollHeight: settings.scrollHeight,
                overflowY: window.getComputedStyle(settings).overflowY
            },
            colsCount: cols.length,
            col0: cols[0] ? {
                clientHeight: cols[0].clientHeight,
                scrollHeight: cols[0].scrollHeight,
                overflowY: window.getComputedStyle(cols[0]).overflowY
            } : null
        };
    }""")
    print("res:", res)

    # Test mouse wheel scrolling
    center_box = page.locator(".st-key-nc-center").bounding_box()
    page.mouse.move(
        center_box["x"] + center_box["width"] / 2, center_box["y"] + center_box["height"] / 2
    )
    page.mouse.wheel(0, 500)
    time.sleep(0.5)
    scroll_top = page.evaluate('() => document.querySelector(".st-key-nc-center").scrollTop')
    print("center scrollTop after wheel:", scroll_top)

    browser.close()
