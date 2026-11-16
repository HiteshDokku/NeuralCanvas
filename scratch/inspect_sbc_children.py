from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const sbc = document.querySelector('[data-testid="stSidebarContent"]');
        return Array.from(sbc.children).map(c => {
            const r = c.getBoundingClientRect();
            return {
                tag: c.tagName,
                className: c.className,
                testId: c.getAttribute('data-testid'),
                rect: { top: r.top, bottom: r.bottom, height: r.height }
            };
        });
    }""")
    import pprint

    pprint.pprint(res)
    browser.close()
