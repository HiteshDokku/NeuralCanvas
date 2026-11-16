import pprint

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const dock = document.querySelector('.st-key-nc-rail-dock');
        const dockWrap = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)');
        const devLine = document.querySelector('.sidebar-device-line');
        const btn = document.querySelector('.st-key-btn_stylize button') || document.querySelector('[data-testid="stBaseButton-primary"]');

        const getInfo = (el) => {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            const cs = window.getComputedStyle(el);
            return {
                tag: el.tagName,
                className: el.className,
                rect: { top: r.top, bottom: r.bottom, height: r.height, left: r.left, right: r.right },
                display: cs.display,
                position: cs.position,
                marginTop: cs.marginTop,
                marginBottom: cs.marginBottom,
                paddingTop: cs.paddingTop,
                paddingBottom: cs.paddingBottom,
                lineHeight: cs.lineHeight,
                height: cs.height,
                zIndex: cs.zIndex,
                transform: cs.transform
            };
        };

        return {
            dock: getInfo(dock),
            dockWrap: getInfo(dockWrap),
            devLine: getInfo(devLine),
            btn: getInfo(btn),
            btnParent: getInfo(btn ? btn.parentElement : null),
            btnContainer: getInfo(btn ? btn.closest('[data-testid="stElementContainer"]') : null),
            devLineContainer: getInfo(devLine ? devLine.closest('[data-testid="stElementContainer"]') : null),
            overlap: (devLine && btn) ? (devLine.getBoundingClientRect().bottom - btn.getBoundingClientRect().top) : null
        };
    }""")

    pprint.pprint(res)
    browser.close()
