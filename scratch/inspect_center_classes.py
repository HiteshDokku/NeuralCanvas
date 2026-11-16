import pprint

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const center = document.querySelector('.st-key-nc-center');
        if (!center) return { error: "no center" };

        const all = Array.from(center.querySelectorAll('*')).map(el => ({
            tag: el.tagName,
            className: el.className,
            testId: el.getAttribute('data-testid'),
            id: el.id
        }));

        return {
            classes: Array.from(new Set(all.map(a => a.className).filter(Boolean))),
            testIds: Array.from(new Set(all.map(a => a.testId).filter(Boolean)))
        };
    }""")
    pprint.pprint(res)
    browser.close()
