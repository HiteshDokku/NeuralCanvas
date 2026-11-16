import time

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stSidebarContent"]')
    time.sleep(2)

    diag = page.evaluate("""() => {
        const sb = document.querySelector('[data-testid="stSidebarContent"]');
        const stylizeBtn = document.querySelector('[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]')
            || document.querySelector('[data-testid="stSidebar"] button');
        const btnContainer = stylizeBtn ? stylizeBtn.closest('[data-testid="stElementContainer"]') : null;
        const devLine = document.querySelector('.sidebar-device-line');
        const devContainer = devLine ? devLine.closest('[data-testid="stElementContainer"]') : null;

        // Ancestors of btnContainer up to stSidebarContent
        const ancestors = [];
        let curr = btnContainer;
        while (curr && curr !== document.body) {
            const cs = window.getComputedStyle(curr);
            const r = curr.getBoundingClientRect();
            ancestors.push({
                tag: curr.tagName,
                testId: curr.getAttribute('data-testid'),
                className: typeof curr.className === 'string' ? curr.className : '',
                position: cs.position,
                top: cs.top,
                bottom: cs.bottom,
                height: cs.height,
                overflow: cs.overflow,
                overflowY: cs.overflowY,
                display: cs.display,
                rect: { top: r.top, bottom: r.bottom, height: r.height, y: r.y }
            });
            if (curr.getAttribute('data-testid') === 'stSidebarContent') break;
            curr = curr.parentElement;
        }

        // Measure rects at scrollTop 0, half, bottom
        sb.scrollTop = 0;
        const r_top = btnContainer ? btnContainer.getBoundingClientRect() : null;
        const dev_top = devContainer ? devContainer.getBoundingClientRect() : null;
        const scrollH = sb.scrollHeight;
        const clientH = sb.clientHeight;
        const maxScroll = scrollH - clientH;

        sb.scrollTop = Math.floor(maxScroll / 2);
        const r_mid = btnContainer ? btnContainer.getBoundingClientRect() : null;
        const dev_mid = devContainer ? devContainer.getBoundingClientRect() : null;

        sb.scrollTop = maxScroll;
        const r_bot = btnContainer ? btnContainer.getBoundingClientRect() : null;
        const dev_bot = devContainer ? devContainer.getBoundingClientRect() : null;

        return {
            scrollH,
            clientH,
            maxScroll,
            ancestors,
            rects: {
                btn: { top: r_top, mid: r_mid, bot: r_bot },
                dev: { top: dev_top, mid: dev_mid, bot: dev_bot }
            }
        };
    }""")

    print("=== SCROLL METRICS ===")
    print(
        f"scrollHeight: {diag['scrollH']}, clientHeight: {diag['clientH']}, maxScroll: {diag['maxScroll']}"
    )

    print("\n=== ANCESTORS OF STYLIZE BUTTON CONTAINER ===")
    for i, a in enumerate(diag["ancestors"]):
        print(f"Ancestor {i}: <{a['tag']}> data-testid={a['testId']} class='{a['className']}'")
        print(
            f"  position: {a['position']}, display: {a['display']}, overflow: {a['overflow']}, overflowY: {a['overflowY']}"
        )
        print(f"  computed top: {a['top']}, bottom: {a['bottom']}, height: {a['height']}")
        print(
            f"  rect: top={a['rect']['top']}, bottom={a['rect']['bottom']}, height={a['rect']['height']}"
        )

    print("\n=== RECTS AT SCROLL POSITIONS ===")
    print("Stylize Button container:")
    print("  scrollTop 0:   ", diag["rects"]["btn"]["top"])
    print("  scrollTop mid: ", diag["rects"]["btn"]["mid"])
    print("  scrollTop bot: ", diag["rects"]["btn"]["bot"])
    print("Device note container:")
    print("  scrollTop 0:   ", diag["rects"]["dev"]["top"])
    print("  scrollTop mid: ", diag["rects"]["dev"]["mid"])
    print("  scrollTop bot: ", diag["rects"]["dev"]["bot"])

    browser.close()
