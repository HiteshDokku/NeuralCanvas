from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const getInfo = (el) => {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            const cs = window.getComputedStyle(el);
            return {
                tag: el.tagName,
                className: el.className,
                rect: { top: r.top, bottom: r.bottom, height: r.height },
                display: cs.display,
                flexDirection: cs.flexDirection,
                height: cs.height,
                minHeight: cs.minHeight
            };
        };

        const sb = document.querySelector('[data-testid="stSidebar"]');
        const sbc = document.querySelector('[data-testid="stSidebarContent"]');
        const sbu = document.querySelector('[data-testid="stSidebarUserContent"]');
        const dock = document.querySelector('.st-key-nc-rail-dock');
        const dockWrap = dock.closest('[data-testid="stLayoutWrapper"]');
        const vb = dockWrap ? dockWrap.parentElement : null;

        return {
            vh: window.innerHeight,
            sb: getInfo(sb),
            sbc: getInfo(sbc),
            sbu: getInfo(sbu),
            vb: getInfo(vb),
            dockWrap: getInfo(dockWrap),
            dock: getInfo(dock)
        };
    }""")
    import pprint

    pprint.pprint(res)
    browser.close()
