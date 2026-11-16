from playwright.sync_api import sync_playwright

candidate_css = """
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
    display: none !important;
}

[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    display: flex !important;
    flex-direction: column !important;
    height: 100dvh !important;
    max-height: 100dvh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    overscroll-behavior: contain !important;
    padding-top: 0.75rem !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    padding-bottom: 0 !important;
    box-sizing: border-box !important;
    position: relative !important;
}

[data-testid="stSidebar"] [data-testid="stSidebarUserContent"],
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div,
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] {
    display: flex !important;
    flex-direction: column !important;
    flex: 1 1 auto !important;
    min-height: 100% !important;
    padding: 0 !important;
    margin: 0 !important;
    gap: 0 !important;
}

.st-key-nc-rail-content {
    flex: 1 0 auto !important;
    padding: 0 0.75rem 116px 0.75rem !important;
    box-sizing: border-box !important;
    width: 100% !important;
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

.st-key-nc-rail-dock {
    padding: 8px 12px 10px 12px !important;
    background-color: #131313 !important;
    box-sizing: border-box !important;
    width: 100% !important;
}
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    for w, h in [(1366, 768), (1280, 650), (1920, 1080)]:
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto("http://localhost:8501", wait_until="networkidle")
        page.wait_for_selector(".st-key-nc-rail-dock")

        # Inject CSS
        page.evaluate(f"""() => {{
            const style = document.createElement('style');
            style.id = 'candidate-css';
            style.textContent = `{candidate_css}`;
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
                    dockTop: dr.top,
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
