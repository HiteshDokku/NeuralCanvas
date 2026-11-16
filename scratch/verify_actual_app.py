import time
from pathlib import Path

from playwright.sync_api import sync_playwright

output_dir = Path("outputs/review")
output_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()

    # 1. Multi-viewport evaluation: 1366x768, 1280x650, 1920x1080
    viewports = [(1366, 768), (1280, 650), (1920, 1080)]
    for w, h in viewports:
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto("http://localhost:8501", wait_until="networkidle")
        page.wait_for_selector(".st-key-nc-rail-dock", timeout=15000)
        time.sleep(1.5)

        # Top
        page.evaluate(
            "() => { const sb = document.querySelector('[data-testid=\"stSidebarContent\"]'); sb.scrollTop = 0; }"
        )
        time.sleep(0.3)
        page.screenshot(path=str(output_dir / f"ui5_rail_top_{w}x{h}.png"))

        res_top = page.evaluate("""() => {
            const vh = window.innerHeight;
            const sb = document.querySelector('[data-testid="stSidebarContent"]');
            const dock = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
                || document.querySelector('.st-key-nc-rail-dock');
            const dr = dock.getBoundingClientRect();
            return {
                vh,
                scrollTop: sb.scrollTop,
                dockBottom: dr.bottom,
                dockTop: dr.top,
                dockHeight: dr.height,
                diffFromVh: Math.round(vh - dr.bottom)
            };
        }""")

        # Mid
        page.evaluate(
            "() => { const sb = document.querySelector('[data-testid=\"stSidebarContent\"]'); sb.scrollTop = Math.floor((sb.scrollHeight - sb.clientHeight) / 2); }"
        )
        time.sleep(0.3)
        page.screenshot(path=str(output_dir / f"ui5_rail_mid_{w}x{h}.png"))

        res_mid = page.evaluate("""() => {
            const vh = window.innerHeight;
            const sb = document.querySelector('[data-testid="stSidebarContent"]');
            const dock = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
                || document.querySelector('.st-key-nc-rail-dock');
            const dr = dock.getBoundingClientRect();
            return {
                vh,
                scrollTop: sb.scrollTop,
                dockBottom: dr.bottom,
                dockTop: dr.top,
                dockHeight: dr.height,
                diffFromVh: Math.round(vh - dr.bottom)
            };
        }""")

        # Bottom
        page.evaluate(
            "() => { const sb = document.querySelector('[data-testid=\"stSidebarContent\"]'); sb.scrollTop = sb.scrollHeight - sb.clientHeight; }"
        )
        time.sleep(0.3)
        page.screenshot(path=str(output_dir / f"ui5_rail_bottom_{w}x{h}.png"))

        res_bot = page.evaluate("""() => {
            const vh = window.innerHeight;
            const sb = document.querySelector('[data-testid="stSidebarContent"]');
            const dock = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
                || document.querySelector('.st-key-nc-rail-dock');
            const dr = dock.getBoundingClientRect();
            const keepColors = Array.from(document.querySelectorAll('label')).find(l => l.textContent.includes('Keep photo colors'));
            const kr = keepColors ? keepColors.getBoundingClientRect() : null;

            // elementFromPoint checks:
            const xCenter = dr.left + dr.width / 2;
            const yAbove = dr.top - 4;
            const elAbove = document.elementFromPoint(xCenter, yAbove);

            const yInside = dr.top + 4;
            const elInside = document.elementFromPoint(xCenter, yInside);

            return {
                vh,
                scrollH: sb.scrollHeight,
                clientH: sb.clientHeight,
                scrollTop: sb.scrollTop,
                dockBottom: dr.bottom,
                dockTop: dr.top,
                dockHeight: dr.height,
                diffFromVh: Math.round(vh - dr.bottom),
                keepColorsBottom: kr ? kr.bottom : null,
                keepColorsTop: kr ? kr.top : null,
                gapKeepColorsToDock: kr ? Math.round(dr.top - kr.bottom) : null,
                elAboveTag: elAbove ? elAbove.tagName : null,
                elAboveText: elAbove ? elAbove.textContent.trim().slice(0, 35) : null,
                elInsideTag: elInside ? elInside.tagName : null,
                elInsideClass: elInside ? elInside.className : null
            };
        }""")

        print(f"\n=================== VIEWPORT {w}x{h} ===================")
        print(f"ScrollH: {res_bot['scrollH']}, ClientH: {res_bot['clientH']}")
        print(f"TOP: dockBottom={res_top['dockBottom']}, diffFromVh={res_top['diffFromVh']}px")
        print(f"MID: dockBottom={res_mid['dockBottom']}, diffFromVh={res_mid['diffFromVh']}px")
        print(f"BOT: dockBottom={res_bot['dockBottom']}, diffFromVh={res_bot['diffFromVh']}px")
        print(f"BOT gap Keep colors to dock: {res_bot['gapKeepColorsToDock']}px")
        print(f"Element 4px above dock: <{res_bot['elAboveTag']}> '{res_bot['elAboveText']}'")
        print(
            f"Element 4px inside dock: <{res_bot['elInsideTag']}> class='{res_bot['elInsideClass']}'"
        )

        page.close()

    # 2. Text & Tooltip checks
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock", timeout=15000)
    time.sleep(1)

    checks = page.evaluate("""() => {
        const devLine = document.querySelector('.sidebar-device-line');
        const radioOpts = Array.from(document.querySelectorAll('[data-testid="stSidebar"] [data-testid="stRadioOption"]'));
        const uploaderSpans = Array.from(document.querySelectorAll('[data-testid="stSidebar"] [data-testid="stFileUploader"] section span'));
        const uploaderHint = uploaderSpans.find(s => s.children.length === 0 && s.textContent.includes('JPG'));

        const optDetails = radioOpts.map(opt => {
            const p = opt.querySelector('p');
            return {
                title: opt.getAttribute('title'),
                text: p ? p.textContent.trim() : null,
                overflow: window.getComputedStyle(opt).overflow,
                textOverflow: p ? window.getComputedStyle(p).textOverflow : null
            };
        });

        return {
            devLineText: devLine ? devLine.textContent.trim() : null,
            devLineTitle: devLine ? devLine.getAttribute('title') : null,
            devLineTextOverflow: devLine ? window.getComputedStyle(devLine).textOverflow : null,
            optCount: radioOpts.length,
            optSample: optDetails.slice(0, 3),
            uploaderSmallText: uploaderHint ? uploaderHint.textContent.trim() : null,
            uploaderSmallTitle: uploaderHint ? uploaderHint.getAttribute('title') : null,
            uploaderSmallTextOverflow: uploaderHint ? window.getComputedStyle(uploaderHint).textOverflow : null
        };
    }""")

    print("\n=================== TEXT & TOOLTIPS ===================")
    print("Device line text:", checks["devLineText"])
    print("Device line title:", checks["devLineTitle"])
    print("Device line textOverflow:", checks["devLineTextOverflow"])
    print("Radio options count:", checks["optCount"])
    print("Radio options sample:", checks["optSample"])
    print("Uploader hint text:", checks["uploaderSmallText"])
    print("Uploader hint title:", checks["uploaderSmallTitle"])
    print("Uploader hint textOverflow:", checks["uploaderSmallTextOverflow"])

    # 3. Sidebar resize handle test
    sidebar_w_before = page.evaluate(
        "() => document.querySelector('[data-testid=\"stSidebar\"]').getBoundingClientRect().width"
    )
    resize_handle = page.query_selector('[data-testid="stSidebarResizeHandle"]')
    if resize_handle:
        box = resize_handle.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + 100, box["y"] + box["height"] / 2)
        page.mouse.up()
        time.sleep(0.5)
        sidebar_w_after = page.evaluate(
            "() => document.querySelector('[data-testid=\"stSidebar\"]').getBoundingClientRect().width"
        )
        print(
            f"\nSidebar resize test: before={sidebar_w_before}px, after={sidebar_w_after}px (diff={sidebar_w_after - sidebar_w_before}px)"
        )
    else:
        print("\nSidebar resize handle not found")

    # 4. Stylize button -> Cancel button dock test
    sel = page.locator('[data-testid="stSelectbox"]')
    sel.click()
    time.sleep(0.5)

    opt = page.locator(
        'div[role="option"]:has-text("dog.jpg"), li:has-text("dog.jpg"), div:has-text("dog.jpg")'
    ).last
    opt.click()
    time.sleep(1)

    btn_stylize = page.locator('[data-testid="stSidebar"] [data-testid="stBaseButton-primary"]')
    btn_stylize.click()
    time.sleep(1.5)

    cancel_check = page.evaluate("""() => {
        const vh = window.innerHeight;
        const cancelBtn = Array.from(document.querySelectorAll('[data-testid="stSidebar"] button')).find(b => b.textContent.trim() === 'Cancel');
        const dock = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
            || document.querySelector('.st-key-nc-rail-dock');
        const dr = dock ? dock.getBoundingClientRect() : null;
        const cr = cancelBtn ? cancelBtn.getBoundingClientRect() : null;

        return {
            hasCancelBtn: !!cancelBtn,
            cancelText: cancelBtn ? cancelBtn.textContent.trim() : null,
            dockBottom: dr ? dr.bottom : null,
            diffFromVh: dr ? Math.round(vh - dr.bottom) : null,
            cancelInsideDock: (dr && cr) ? (cr.top >= dr.top && cr.bottom <= dr.bottom) : false
        };
    }""")
    print("\n=================== CANCEL BUTTON DOCK CHECK ===================")
    print("Cancel button test:", cancel_check)

    cancel_btn = page.locator(".st-key-btn_cancel button")
    if cancel_btn.count() > 0:
        cancel_btn.click()
        time.sleep(1)

    page.close()
    browser.close()
