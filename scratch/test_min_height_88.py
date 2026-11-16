from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    for w, h in [(1366, 768), (1280, 650), (1920, 1080)]:
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto("http://localhost:8501", wait_until="networkidle")
        page.wait_for_selector(".st-key-nc-rail-dock")

        test_css = """
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
            min-height: calc(100dvh - 88px) !important;
            display: flex !important;
            flex-direction: column !important;
        }
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div {
            min-height: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            flex: 1 1 auto !important;
        }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"]:not(.st-key-nc-rail-content):not(.st-key-nc-rail-dock) {
            min-height: 100% !important;
            display: flex !important;
            flex-direction: column !important;
            flex: 1 1 auto !important;
        }
        [data-testid="stSidebar"] [data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock) {
            margin-top: auto !important;
            position: sticky !important;
            bottom: 0 !important;
            z-index: 999 !important;
            width: 100% !important;
            background-color: #131313 !important;
            border-top: 1px solid #2A2A2A !important;
            box-sizing: border-box !important;
        }
        """

        page.evaluate(f"""() => {{
            const style = document.createElement('style');
            style.textContent = `{test_css}`;
            document.head.appendChild(style);
        }}""")

        res = page.evaluate("""() => {
            const vh = window.innerHeight;
            const sb = document.querySelector('[data-testid="stSidebarContent"]');
            const dock = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
                || document.querySelector('.st-key-nc-rail-dock');
            const keepColors = Array.from(document.querySelectorAll('label')).find(l => l.textContent.includes('Keep photo colors'));

            const getMetrics = () => {
                const dr = dock.getBoundingClientRect();
                const kr = keepColors ? keepColors.getBoundingClientRect() : null;
                return {
                    dockBottom: dr.bottom,
                    diffFromVh: Math.round(vh - dr.bottom),
                    gapKeepColors: kr ? Math.round(dr.top - kr.bottom) : null
                };
            };

            sb.scrollTop = 0;
            const m_top = getMetrics();

            const maxScroll = sb.scrollHeight - sb.clientHeight;
            sb.scrollTop = Math.floor(maxScroll / 2);
            const m_mid = getMetrics();

            sb.scrollTop = maxScroll;
            const m_bot = getMetrics();

            return {
                vh,
                scrollH: sb.scrollHeight,
                clientH: sb.clientHeight,
                m_top,
                m_mid,
                m_bot
            };
        }""")
        print(f"\n=================== VIEWPORT {w}x{h} ===================")
        print(f"ScrollH: {res['scrollH']}, ClientH: {res['clientH']}")
        print(f"TOP: dockBottom={res['m_top']['dockBottom']}, diff={res['m_top']['diffFromVh']}px")
        print(f"MID: dockBottom={res['m_mid']['dockBottom']}, diff={res['m_mid']['diffFromVh']}px")
        print(
            f"BOT: dockBottom={res['m_bot']['dockBottom']}, diff={res['m_bot']['diffFromVh']}px, gapKeepColors={res['m_bot']['gapKeepColors']}px"
        )
        page.close()
    browser.close()
