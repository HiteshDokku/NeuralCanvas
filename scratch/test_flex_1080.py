from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        // Let's test making stSidebarHeader display: none
        const hdr = document.querySelector('[data-testid="stSidebarHeader"]');
        if (hdr) hdr.style.display = 'none';

        const sbc = document.querySelector('[data-testid="stSidebarContent"]');
        sbc.style.display = 'flex';
        sbc.style.flexDirection = 'column';
        sbc.style.height = '100dvh';

        const sbu = document.querySelector('[data-testid="stSidebarUserContent"]');
        sbu.style.display = 'flex';
        sbu.style.flexDirection = 'column';
        sbu.style.flex = '1 1 auto';
        sbu.style.minHeight = '100%';

        const vb = sbu.querySelector('[data-testid="stVerticalBlock"]');
        vb.style.display = 'flex';
        vb.style.flexDirection = 'column';
        vb.style.flex = '1 1 auto';
        vb.style.minHeight = '100%';

        const content = document.querySelector('.st-key-nc-rail-content');
        content.style.flex = '1 0 auto';

        const dockWrap = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)');
        dockWrap.style.marginTop = 'auto';
        dockWrap.style.position = 'sticky';
        dockWrap.style.bottom = '0';

        const vh = window.innerHeight;
        const dr = dockWrap.getBoundingClientRect();
        const vbr = vb.getBoundingClientRect();
        const sbur = sbu.getBoundingClientRect();

        return {
            vh,
            sburBottom: sbur.bottom,
            vbrBottom: vbr.bottom,
            dockBottom: dr.bottom,
            diffFromVh: Math.round(vh - dr.bottom)
        };
    }""")
    print("Flex test at 1080:", res)
    browser.close()
