from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const sbu = document.querySelector('[data-testid="stSidebarUserContent"]');
        return Array.from(sbu.children).map(c => ({
            tag: c.tagName,
            testId: c.getAttribute('data-testid'),
            className: c.className,
            csDisplay: window.getComputedStyle(c).display,
            height: c.getBoundingClientRect().height
        }));
    }""")
    import pprint

    pprint.pprint(res)
    browser.close()
