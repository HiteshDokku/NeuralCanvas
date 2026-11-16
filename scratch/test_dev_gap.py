import pprint

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const dock = document.querySelector('.st-key-nc-rail-dock');
        const devLine = document.querySelector('.sidebar-device-line');
        const btn = document.querySelector('.st-key-nc-rail-dock button');

        const devContainer = devLine ? devLine.closest('[data-testid="stElementContainer"]') : null;
        const btnContainer = btn ? btn.closest('[data-testid="stElementContainer"]') : null;

        const r = (el) => el ? el.getBoundingClientRect() : null;

        return {
            dockR: r(dock),
            devLineR: r(devLine),
            devContainerR: r(devContainer),
            btnContainerR: r(btnContainer),
            btnR: r(btn),
            gapContainers: (devContainer && btnContainer) ? (btnContainer.getBoundingClientRect().top - devContainer.getBoundingClientRect().bottom) : null,
            gapVisual: (devLine && btn) ? (btn.getBoundingClientRect().top - devLine.getBoundingClientRect().bottom) : null
        };
    }""")
    pprint.pprint(res)
    browser.close()
