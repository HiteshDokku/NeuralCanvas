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
            gap: 0 !important;
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
            const dock = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
                || document.querySelector('.st-key-nc-rail-dock');
            const dr = dock.getBoundingClientRect();
            const xCenter = dr.left + dr.width / 2;
            const yAbove = dr.top - 4;
            const elAbove = document.elementFromPoint(xCenter, yAbove);
            const yInside = dr.top + 4;
            const elInside = document.elementFromPoint(xCenter, yInside);

            return {
                yAbove,
                elAboveTag: elAbove ? elAbove.tagName : null,
                elAboveText: elAbove ? elAbove.textContent.trim().slice(0, 40) : null,
                elAboveClass: elAbove ? elAbove.className : null,
                yInside,
                elInsideTag: elInside ? elInside.tagName : null,
                elInsideText: elInside ? elInside.textContent.trim().slice(0, 40) : null,
                elInsideClass: elInside ? elInside.className : null
            };
        }""")
        print(f"\n=================== VIEWPORT {w}x{h} elementFromPoint ===================")
        print("Above 4px:", res["elAboveTag"], res["elAboveClass"], res["elAboveText"])
        print("Inside 4px:", res["elInsideTag"], res["elInsideClass"], res["elInsideText"])
        page.close()
    browser.close()
