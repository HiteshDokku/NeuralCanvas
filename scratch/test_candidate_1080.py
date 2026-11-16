from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        // Apply candidate styles
        const style = document.createElement('style');
        style.textContent = `
            [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
                display: flex !important;
                flex-direction: column !important;
                flex: 1 1 auto !important;
                min-height: 100% !important;
            }
            [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > [data-testid="stVerticalBlock"] {
                display: flex !important;
                flex-direction: column !important;
                flex: 1 1 auto !important;
                min-height: 100% !important;
                gap: 0 !important;
            }
            .st-key-nc-rail-content {
                flex: 1 0 auto !important;
            }
            [data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock) {
                position: sticky !important;
                bottom: 0 !important;
                margin-top: auto !important;
                z-index: 999 !important;
                width: 100% !important;
                background-color: #131313 !important;
                border-top: 1px solid #2A2A2A !important;
                box-sizing: border-box !important;
            }
        `;
        document.head.appendChild(style);

        const vh = window.innerHeight;
        const dock = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
            || document.querySelector('.st-key-nc-rail-dock');
        const dr = dock.getBoundingClientRect();
        return {
            vh,
            dockBottom: dr.bottom,
            diffFromVh: Math.round(vh - dr.bottom)
        };
    }""")
    print("Candidate style test at 1920x1080:", res)
    browser.close()
