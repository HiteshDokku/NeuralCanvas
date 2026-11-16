from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const style = document.createElement('style');
        style.textContent = `
            .st-key-nc-rail-dock {
                display: flex !important;
                flex-direction: column !important;
                gap: 6px !important;
            }
            .st-key-nc-rail-dock [data-testid="stElementContainer"] {
                margin: 0 !important;
                padding: 0 !important;
            }
            .st-key-nc-rail-dock [data-testid="stMarkdownContainer"] {
                margin-bottom: 0 !important;
            }
            .sidebar-device-line {
                margin: 0 !important;
            }
            .st-key-nc-rail-dock button {
                margin: 0 !important;
                z-index: auto !important;
                transform: none !important;
            }
        `;
        document.head.appendChild(style);

        const devLine = document.querySelector('.sidebar-device-line');
        const btn = document.querySelector('.st-key-nc-rail-dock button');

        const dr = devLine.getBoundingClientRect();
        const br = btn.getBoundingClientRect();

        return {
            devLineBottom: dr.bottom,
            btnTop: br.top,
            gapBetweenDevLineAndBtn: br.top - dr.bottom,
            devLineRect: dr,
            btnRect: br
        };
    }""")
    import pprint

    pprint.pprint(res)
    browser.close()
