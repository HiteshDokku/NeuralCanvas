from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const content = document.querySelector('.st-key-nc-rail-content');
        const dock = document.querySelector('.st-key-nc-rail-dock');
        const keepColors = Array.from(document.querySelectorAll('label')).find(l => l.textContent.includes('Keep photo colors'));
        const sb = document.querySelector('[data-testid="stSidebarContent"]');

        const cr = content ? content.getBoundingClientRect() : null;
        const cs = content ? window.getComputedStyle(content) : null;
        const kr = keepColors ? keepColors.getBoundingClientRect() : null;
        const dr = dock ? dock.getBoundingClientRect() : null;

        return {
            contentPadding: cs ? cs.padding : null,
            contentHeight: cr ? cr.height : null,
            contentBottom: cr ? cr.bottom : null,
            keepColorsBottom: kr ? kr.bottom : null,
            dockTop: dr ? dr.top : null,
            gapInsideContent: (cr && kr) ? Math.round(cr.bottom - kr.bottom) : null,
            gapToDock: (dr && kr) ? Math.round(dr.top - kr.bottom) : null,
            sbScrollH: sb.scrollHeight,
            sbClientH: sb.clientHeight,
            sbScrollTop: sb.scrollTop
        };
    }""")
    import pprint

    pprint.pprint(res)
    browser.close()
