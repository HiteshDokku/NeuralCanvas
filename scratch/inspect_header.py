from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const hdr = document.querySelector('[data-testid="stSidebarHeader"]');
        return {
            innerHTML: hdr ? hdr.innerHTML : null,
            childrenCount: hdr ? hdr.children.length : 0,
            rect: hdr ? hdr.getBoundingClientRect() : null,
            computedStyle: hdr ? {
                display: window.getComputedStyle(hdr).display,
                height: window.getComputedStyle(hdr).height,
                padding: window.getComputedStyle(hdr).padding
            } : null
        };
    }""")
    import pprint

    pprint.pprint(res)
    browser.close()
