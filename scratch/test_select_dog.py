import time

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    # Click the selectbox input
    sel = page.locator('[data-testid="stSelectbox"]')
    sel.click()
    time.sleep(0.5)

    # In Streamlit, dropdown options are rendered in a virtual list with [data-testid="stSelectboxVirtualDropdown"] or [role="listbox"]
    opt = page.locator(
        'div[role="option"]:has-text("dog.jpg"), li:has-text("dog.jpg"), div:has-text("dog.jpg")'
    ).last
    opt.click()
    time.sleep(1)

    # Verify dog.jpg is selected
    val = page.evaluate("() => document.querySelector('[data-testid=\"stSelectbox\"]').textContent")
    print("Selectbox text after selection:", val)

    # Now click Stylize
    btn_stylize = page.locator('[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]')
    btn_stylize.click()
    time.sleep(1.5)

    # Check Cancel button
    res = page.evaluate("""() => {
        const vh = window.innerHeight;
        const cancelBtn = Array.from(document.querySelectorAll('[data-testid="stSidebar"] button')).find(b => b.textContent.trim() === 'Cancel');
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
    print("Cancel run check:", res)

    # Click Cancel to stop the run cleanly
    cancel_btn = page.locator(".st-key-btn_cancel button")
    if cancel_btn.count() > 0:
        cancel_btn.click()
        time.sleep(1)

    browser.close()
