import time

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    for w, h in [(1366, 768), (1280, 650), (1920, 1080)]:
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto("http://localhost:8505")
        page.wait_for_selector(".st-key-nc-rail-dock")
        time.sleep(1)

        res = page.evaluate("""() => {
            const vh = window.innerHeight;
            const sb = document.querySelector('[data-testid="stSidebarContent"]');
            const dockWrapper = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
                || document.querySelector('.st-key-nc-rail-dock');
            const keepColors = Array.from(document.querySelectorAll('label')).find(l => l.textContent.includes('Keep photo colors'));

            const getMetrics = () => {
                const dr = dockWrapper.getBoundingClientRect();
                const kr = keepColors ? keepColors.getBoundingClientRect() : null;
                return {
                    dockBottom: dr.bottom,
                    dockTop: dr.top,
                    dockHeight: dr.height,
                    diffBottom: Math.round(vh - dr.bottom),
                    keepColorsBottom: kr ? kr.bottom : null,
                    keepColorsTop: kr ? kr.top : null,
                    gapKeepColorsToDock: kr ? Math.round(dr.top - kr.bottom) : null
                };
            };

            sb.scrollTop = 0;
            const m_top = getMetrics();

            const maxScroll = sb.scrollHeight - sb.clientHeight;
            sb.scrollTop = Math.floor(maxScroll / 2);
            const m_mid = getMetrics();

            sb.scrollTop = maxScroll;
            const m_bot = getMetrics();

            // elementFromPoint checks:
            const dr = dockWrapper.getBoundingClientRect();
            const xCenter = dr.left + dr.width / 2;
            const yAbove = dr.top - 4;
            const elAbove = document.elementFromPoint(xCenter, yAbove);

            const yInside = dr.top + 4;
            const elInside = document.elementFromPoint(xCenter, yInside);

            return {
                vh,
                scrollH: sb.scrollHeight,
                clientH: sb.clientHeight,
                m_top,
                m_mid,
                m_bot,
                elAboveTag: elAbove ? elAbove.tagName : null,
                elAboveText: elAbove ? elAbove.textContent.trim().slice(0, 30) : null,
                elInsideTag: elInside ? elInside.tagName : null,
                elInsideClass: elInside ? elInside.className : null,
            };
        }""")

        print(f"\n=================== VIEWPORT {w}x{h} ===================")
        print(f"Sidebar scrollH: {res['scrollH']}, clientH: {res['clientH']}")
        print(
            f"Top: dockBottom={res['m_top']['dockBottom']}, diffFromVh={res['m_top']['diffBottom']}px"
        )
        print(
            f"Mid: dockBottom={res['m_mid']['dockBottom']}, diffFromVh={res['m_mid']['diffBottom']}px"
        )
        print(
            f"Bot: dockBottom={res['m_bot']['dockBottom']}, diffFromVh={res['m_bot']['diffBottom']}px"
        )
        print(f"Bot gap Keep colors to dock: {res['m_bot']['gapKeepColorsToDock']}px")
        print(f"Element 4px above dock: <{res['elAboveTag']}> '{res['elAboveText']}'")
        print(f"Element 4px inside dock: <{res['elInsideTag']}> class='{res['elInsideClass']}'")
        page.close()

    browser.close()
