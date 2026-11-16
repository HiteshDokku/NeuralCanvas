import time

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    # Select sample photo dog.jpg
    content_sel = page.locator(".st-key-select_content_source")
    content_sel.click()
    page.locator('li:has-text("dog.jpg")').click()
    time.sleep(1)

    # Click Stylize
    btn = page.locator(".st-key-btn_stylize button")
    btn.click()
    time.sleep(1)

    # Check Cancel button
    res = page.evaluate("""() => {
        const vh = window.innerHeight;
        const cancelBtn = document.querySelector('.st-key-btn_cancel button')
            || Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Cancel');
        const dock = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
            || document.querySelector('.st-key-nc-rail-dock');
        const dr = dock ? dock.getBoundingClientRect() : null;
        const cr = cancelBtn ? cancelBtn.getBoundingClientRect() : null;

        return {
            hasCancelBtn: !!cancelBtn,
            cancelText: cancelBtn ? cancelBtn.textContent.trim() : null,
            dockBottom: dr ? dr.bottom : null,
            diffFromVh: dr ? Math.round(vh - dr.bottom) : null,
            cancelInsideDock: (dr && cr) ? (cr.top >= dr.top && cr.bottom <= dr.bottom) : false
        };
    }""")
    print("Cancel button run check:", res)

    # Now click Cancel to clean up
    cancel_btn = page.locator(".st-key-btn_cancel button")
    if cancel_btn.count() > 0:
        cancel_btn.click()
        time.sleep(1)

    browser.close()
