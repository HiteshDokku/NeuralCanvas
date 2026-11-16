import pprint

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const devLine = document.querySelector('.sidebar-device-line');
        const container = devLine ? devLine.closest('[data-testid="stElementContainer"]') : null;

        const chain = [];
        let cur = devLine;
        while (cur && cur !== document.body) {
            const cs = window.getComputedStyle(cur);
            const r = cur.getBoundingClientRect();
            chain.push({
                tag: cur.tagName,
                className: cur.className,
                testId: cur.getAttribute('data-testid'),
                rect: { top: r.top, bottom: r.bottom, height: r.height },
                height: cs.height,
                lineHeight: cs.lineHeight,
                overflow: cs.overflow,
                margin: cs.margin,
                padding: cs.padding,
                display: cs.display
            });
            cur = cur.parentElement;
        }
        return chain;
    }""")
    pprint.pprint(res)
    browser.close()
