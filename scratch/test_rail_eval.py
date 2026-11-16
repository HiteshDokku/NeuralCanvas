import time

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8504")
    page.wait_for_selector(".st-key-nc-rail-dock")
    time.sleep(1)

    res = page.evaluate("""() => {
        const vh = window.innerHeight;
        const scrollEl = document.querySelector('.st-key-nc-rail-scroll');
        const dockEl = document.querySelector('.st-key-nc-rail-dock');
        const keepColors = Array.from(document.querySelectorAll('label')).find(l => l.textContent.includes('Keep photo colors'));

        const getMetrics = () => {
            const dr = dockEl.getBoundingClientRect();
            const kr = keepColors ? keepColors.getBoundingClientRect() : null;
            return {
                dockBottom: dr.bottom,
                dockTop: dr.top,
                dockHeight: dr.height,
                diffBottom: vh - dr.bottom,
                keepColorsBottom: kr ? kr.bottom : null,
                keepColorsTop: kr ? kr.top : null,
                gapKeepColorsToDock: kr ? dr.top - kr.bottom : null
            };
        };

        scrollEl.scrollTop = 0;
        const m_top = getMetrics();

        const maxScroll = scrollEl.scrollHeight - scrollEl.clientHeight;
        scrollEl.scrollTop = Math.floor(maxScroll / 2);
        const m_mid = getMetrics();

        scrollEl.scrollTop = maxScroll;
        const m_bot = getMetrics();

        // elementFromPoint checks:
        // 4px above dock top edge:
        const xCenter = dockEl.getBoundingClientRect().left + dockEl.getBoundingClientRect().width / 2;
        const yAbove = dockEl.getBoundingClientRect().top - 4;
        const elAbove = document.elementFromPoint(xCenter, yAbove);

        // 4px inside dock top edge:
        const yInside = dockEl.getBoundingClientRect().top + 4;
        const elInside = document.elementFromPoint(xCenter, yInside);

        return {
            vh,
            scrollClientH: scrollEl.clientHeight,
            scrollScrollH: scrollEl.scrollHeight,
            m_top,
            m_mid,
            m_bot,
            elAboveTag: elAbove ? elAbove.tagName : null,
            elAboveClass: elAbove ? elAbove.className : null,
            elInsideTag: elInside ? elInside.tagName : null,
            elInsideClass: elInside ? elInside.className : null,
        };
    }""")

    print("Viewport Height:", res["vh"])
    print("Scroll Container:", res["scrollClientH"], "scrollH:", res["scrollScrollH"])
    print("\nMetrics at scrollTop 0:")
    print("  dock bottom:", res["m_top"]["dockBottom"], "diff from vh:", res["m_top"]["diffBottom"])
    print("\nMetrics at scrollTop mid:")
    print("  dock bottom:", res["m_mid"]["dockBottom"], "diff from vh:", res["m_mid"]["diffBottom"])
    print("\nMetrics at scrollTop bot:")
    print("  dock bottom:", res["m_bot"]["dockBottom"], "diff from vh:", res["m_bot"]["diffBottom"])
    print(
        "  Keep colors top:",
        res["m_bot"]["keepColorsTop"],
        "bottom:",
        res["m_bot"]["keepColorsBottom"],
    )
    print("  Gap keep colors to dock:", res["m_bot"]["gapKeepColorsToDock"])
    print("\nelementFromPoint 4px above dock:", res["elAboveTag"], res["elAboveClass"])
    print("elementFromPoint 4px inside dock:", res["elInsideTag"], res["elInsideClass"])

    browser.close()
