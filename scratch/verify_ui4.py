import os
import shutil
import time

from playwright.sync_api import sync_playwright

OUT_DIR = os.path.abspath("outputs/review")
os.makedirs(OUT_DIR, exist_ok=True)


def save_screen(page, num, name):
    num_path = os.path.join(OUT_DIR, f"{num}_{name}.png")
    plain_path = os.path.join(OUT_DIR, f"{name}.png")
    page.screenshot(path=num_path, full_page=True)
    shutil.copyfile(num_path, plain_path)
    print(f"Saved: {num}_{name}.png and {name}.png ({os.path.getsize(num_path)} bytes)")


with sync_playwright() as p:
    browser = p.chromium.launch()

    # ----------------- TEST 1: 1366x768 Closed & Open ----------------- #
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501")
    page.wait_for_selector(".st-key-nc-center")
    time.sleep(2)

    # Check uploader initial state (Upload custom photo is default)
    uploader_check = page.evaluate("""() => {
        const uploader = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"]');
        if (!uploader) return null;
        const btn = uploader.querySelector('button');
        const icon = uploader.querySelector('[data-testid="stIconMaterial"]');
        const dropzone = uploader.querySelector('[data-testid="stFileUploaderDropzone"]') || uploader.querySelector('section');
        return {
            buttonText: btn ? btn.textContent : null,
            buttonInnerHTML: btn ? btn.innerHTML : null,
            iconFontFamily: icon ? window.getComputedStyle(icon).fontFamily : null,
            dropzoneHeight: dropzone ? dropzone.getBoundingClientRect().height : null
        };
    }""")
    print("Uploader check (initial):", uploader_check)
    save_screen(page, "40", "ui4_uploader_1366x768")

    # Select "dog.jpg" in content source for photo reference tile
    page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').click()
    time.sleep(0.5)
    page.locator('[role="option"]').filter(has_text="dog.jpg").click()
    time.sleep(1)

    # Capture closed state screenshot with photo loaded
    save_screen(page, "37", "ui4_closed_1366x768")

    # Measure selectors (closed)
    counts_closed = page.evaluate("""() => {
        return {
            centerContainers: document.querySelectorAll('.st-key-nc-center').length,
            settingsContainers: document.querySelectorAll('.st-key-nc-settings').length,
            horizontalBlocks: document.querySelectorAll('[data-testid="stHorizontalBlock"]').length,
            columns: document.querySelectorAll('[data-testid="stColumn"]').length,
        };
    }""")
    print("Counts (Settings closed):", counts_closed)

    # Measure center zone properties (closed)
    center_closed = page.evaluate("""() => {
        const c = document.querySelector('.st-key-nc-center');
        const plate = document.querySelector('.result-plate');
        return {
            clientWidth: c.clientWidth,
            clientHeight: c.clientHeight,
            scrollHeight: c.scrollHeight,
            plateHeight: plate.getBoundingClientRect().height,
            overflowY: window.getComputedStyle(c).overflowY
        };
    }""")
    print("Center (Settings closed):", center_closed)

    # Open settings panel
    btn_settings = page.locator("button").filter(has_text="Settings")
    btn_settings.click()
    page.wait_for_selector(".st-key-nc-settings")
    time.sleep(2)

    # Capture open state screenshot
    save_screen(page, "38", "ui4_open_1366x768")

    # Measure selectors (open)
    counts_open = page.evaluate("""() => {
        return {
            centerContainers: document.querySelectorAll('.st-key-nc-center').length,
            settingsContainers: document.querySelectorAll('.st-key-nc-settings').length,
            horizontalBlocks: document.querySelectorAll('[data-testid="stHorizontalBlock"]').length,
            columns: document.querySelectorAll('[data-testid="stColumn"]').length,
        };
    }""")
    print("Counts (Settings open):", counts_open)

    # Invariant test: Elements with height >= 0.85 * vh and overflowY in ('auto', 'scroll')
    tall_scrollers = page.evaluate("""() => {
        const vh = window.innerHeight;
        const all = Array.from(document.querySelectorAll('*'));
        return all.filter(el => {
            const cs = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return (cs.overflowY === 'auto' || cs.overflowY === 'scroll') && rect.height >= 0.85 * vh;
        }).map(el => ({
            tag: el.tagName,
            id: el.id,
            className: typeof el.className === 'string' ? el.className.split(' ').slice(0, 3).join(' ') : '',
            testId: el.getAttribute('data-testid'),
            clientHeight: el.clientHeight,
            scrollHeight: el.scrollHeight
        }));
    }""")
    print("Tall scroll containers count:", len(tall_scrollers))
    for i, s in enumerate(tall_scrollers):
        print(
            f"  Scroller {i + 1}: testId={s['testId']}, class={s['className']}, clientH={s['clientHeight']}, scrollH={s['scrollHeight']}"
        )

    # Measure Right Panel
    settings_metrics = page.evaluate("""() => {
        const s = document.querySelector('.st-key-nc-settings');
        return {
            clientWidth: s.clientWidth,
            clientHeight: s.clientHeight,
            scrollHeight: s.scrollHeight,
            overflowY: window.getComputedStyle(s).overflowY
        };
    }""")
    print("Settings metrics at 1366x768:", settings_metrics)

    # Test wheel scroll on right panel to reach "Reset to preset"
    settings_box = page.locator(".st-key-nc-settings").bounding_box()
    page.mouse.move(
        settings_box["x"] + settings_box["width"] / 2,
        settings_box["y"] + settings_box["height"] / 2,
    )
    page.mouse.wheel(0, 2000)
    time.sleep(0.5)

    settings_scroll_top = page.evaluate(
        '() => document.querySelector(".st-key-nc-settings").scrollTop'
    )
    print("Settings scrollTop after 2000px wheel:", settings_scroll_top)

    reset_btn_visible = page.evaluate("""() => {
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Reset to preset'));
        if (!btn) return false;
        const rect = btn.getBoundingClientRect();
        return rect.top >= 0 && rect.bottom <= window.innerHeight;
    }""")
    print("Reset to preset button visible in viewport:", reset_btn_visible)

    # Test wheel scroll on center zone
    center_box = page.locator(".st-key-nc-center").bounding_box()
    page.mouse.move(
        center_box["x"] + center_box["width"] / 2, center_box["y"] + center_box["height"] / 2
    )
    page.mouse.wheel(0, 500)
    time.sleep(0.5)
    center_scroll_top = page.evaluate('() => document.querySelector(".st-key-nc-center").scrollTop')
    print("Center scrollTop after 500px wheel:", center_scroll_top)

    # Test wheel scroll on left sidebar
    sidebar_box = page.locator('[data-testid="stSidebarContent"]').bounding_box()
    page.mouse.move(
        sidebar_box["x"] + sidebar_box["width"] / 2, sidebar_box["y"] + sidebar_box["height"] / 2
    )
    page.mouse.wheel(0, 2000)
    time.sleep(0.5)
    sidebar_scroll_top = page.evaluate(
        '() => document.querySelector("[data-testid=\\"stSidebarContent\\"]").scrollTop'
    )
    print("Sidebar scrollTop after 2000px wheel:", sidebar_scroll_top)

    # Verify Rail bottom elements visible when scrolled to bottom
    rail_bottom_check = page.evaluate("""() => {
        const vh = window.innerHeight;
        const isVis = (el) => {
            if (!el) return false;
            const r = el.getBoundingClientRect();
            return r.top >= 0 && r.bottom <= vh && r.height > 0;
        };
        const pMode = Array.from(document.querySelectorAll('[data-testid="stSidebar"] label')).find(l => l.textContent.includes('Portrait mode'));
        const kColor = Array.from(document.querySelectorAll('[data-testid="stSidebar"] label')).find(l => l.textContent.includes('Keep photo colors'));
        const devLine = document.querySelector('.sidebar-device-line');
        const stylizeBtn = document.querySelector('[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]');
        return {
            portraitModeVisible: isVis(pMode),
            keepColorsVisible: isVis(kColor),
            deviceLineVisible: isVis(devLine),
            stylizeBtnVisible: isVis(stylizeBtn),
            stylizeText: stylizeBtn ? stylizeBtn.textContent.trim() : null
        };
    }""")
    print("Rail bottom visibility check:", rail_bottom_check)

    # Capture rail scrolled screenshot
    save_screen(page, "39", "ui4_rail_scrolled_1366x768")

    # ----------------- TEST 2: Label & Typo Checks ----------------- #
    label_and_typo = page.evaluate("""() => {
        const labels = Array.from(document.querySelectorAll('.sidebar-section-label')).map(l => {
            const cs = window.getComputedStyle(l);
            const r = l.getBoundingClientRect();
            return {
                text: l.textContent.trim(),
                lineHeight: cs.lineHeight,
                paddingBottom: cs.paddingBottom,
                marginBottom: cs.marginBottom,
                height: r.height,
            };
        });
        const guidance = document.querySelector('.ref-tile-guidance');
        const captions = Array.from(document.querySelectorAll('.ref-tile-caption')).map(c => ({
            text: c.textContent.trim(),
            title: c.getAttribute('title'),
            whiteSpace: window.getComputedStyle(c).whiteSpace,
            overflow: window.getComputedStyle(c).overflow,
            textOverflow: window.getComputedStyle(c).textOverflow
        }));
        return {
            labels: labels,
            guidanceText: guidance ? guidance.textContent.trim() : null,
            captions: captions
        };
    }""")
    print("Labels check:", label_and_typo["labels"])
    print("Guidance note text:", label_and_typo["guidanceText"])
    print("Captions check:", label_and_typo["captions"])

    # ----------------- TEST 3: Resizer Handle Drag & Reset ----------------- #
    # Scroll settings panel back to top
    page.evaluate('() => document.querySelector(".st-key-nc-settings").scrollTop = 0')
    time.sleep(0.5)

    resizer = page.locator(".nc-resize-handle")
    r_box = resizer.bounding_box()
    print("Initial resizer box:", r_box)

    # Drag +80px (drag to the left expands right panel)
    page.mouse.move(r_box["x"] + r_box["width"] / 2, 200)
    page.mouse.down()
    page.mouse.move(r_box["x"] + r_box["width"] / 2 - 80, 200, steps=10)
    page.mouse.up()
    time.sleep(0.5)
    w_after_drag_plus = page.evaluate(
        '() => document.querySelector(".st-key-nc-settings").getBoundingClientRect().width'
    )
    print("Width after +80px drag:", w_after_drag_plus)

    # Drag -80px (drag to the right contracts right panel)
    r_box2 = resizer.bounding_box()
    page.mouse.move(r_box2["x"] + r_box2["width"] / 2, 200)
    page.mouse.down()
    page.mouse.move(r_box2["x"] + r_box2["width"] / 2 + 80, 200, steps=10)
    page.mouse.up()
    time.sleep(0.5)
    w_after_drag_minus = page.evaluate(
        '() => document.querySelector(".st-key-nc-settings").getBoundingClientRect().width'
    )
    print("Width after -80px drag:", w_after_drag_minus)

    # Double-click handle to reset
    r_box3 = resizer.bounding_box()
    page.mouse.dblclick(r_box3["x"] + r_box3["width"] / 2, 200)
    time.sleep(0.5)
    w_after_reset = page.evaluate(
        '() => document.querySelector(".st-key-nc-settings").getBoundingClientRect().width'
    )
    print("Width after double-click reset:", w_after_reset)

    # Native sidebar resize handle drag test
    sidebar_handle = page.locator('[data-testid="stSidebarResizeHandle"]')
    sb_box = sidebar_handle.bounding_box()
    w_sb_before = page.evaluate(
        '() => document.querySelector("[data-testid=\\"stSidebar\\"]").getBoundingClientRect().width'
    )
    page.mouse.move(sb_box["x"] + sb_box["width"] / 2, 200)
    page.mouse.down()
    page.mouse.move(sb_box["x"] + sb_box["width"] / 2 + 50, 200, steps=10)
    page.mouse.up()
    time.sleep(0.5)
    w_sb_after = page.evaluate(
        '() => document.querySelector("[data-testid=\\"stSidebar\\"]").getBoundingClientRect().width'
    )
    print(f"Sidebar width before: {w_sb_before}, after +50px native drag: {w_sb_after}")

    # ----------------- TEST 4: 1920x1080 Viewport (Closed & Open) ----------------- #
    page1080 = browser.new_page(viewport={"width": 1920, "height": 1080})
    page1080.goto("http://localhost:8501")
    page1080.wait_for_selector(".st-key-nc-center")
    time.sleep(2)

    # Measure closed at 1080p
    c1080_closed = page1080.evaluate("""() => {
        const c = document.querySelector('.st-key-nc-center');
        const plate = document.querySelector('.result-plate');
        return {
            clientHeight: c.clientHeight,
            scrollHeight: c.scrollHeight,
            plateHeight: plate.getBoundingClientRect().height,
            hasScroll: c.scrollHeight > c.clientHeight
        };
    }""")
    print("Center at 1920x1080 (closed):", c1080_closed)
    save_screen(page1080, "41", "ui4_closed_1920x1080")

    # Open settings at 1080p
    page1080.locator("button").filter(has_text="Settings").click()
    page1080.wait_for_selector(".st-key-nc-settings")
    time.sleep(2)

    c1080_open = page1080.evaluate("""() => {
        const c = document.querySelector('.st-key-nc-center');
        const s = document.querySelector('.st-key-nc-settings');
        return {
            centerClientH: c.clientHeight,
            centerScrollH: c.scrollHeight,
            centerHasScroll: c.scrollHeight > c.clientHeight,
            settingsClientH: s.clientHeight,
            settingsScrollH: s.scrollHeight,
        };
    }""")
    print("1920x1080 (open):", c1080_open)
    save_screen(page1080, "42", "ui4_open_1920x1080")
    page1080.close()

    # ----------------- TEST 5: 1280x650 Viewport (Closed & Open) ----------------- #
    page650 = browser.new_page(viewport={"width": 1280, "height": 650})
    page650.goto("http://localhost:8501")
    page650.wait_for_selector(".st-key-nc-center")
    time.sleep(2)

    c650_closed = page650.evaluate("""() => {
        const c = document.querySelector('.st-key-nc-center');
        const plate = document.querySelector('.result-plate');
        return {
            clientHeight: c.clientHeight,
            scrollHeight: c.scrollHeight,
            plateHeight: plate.getBoundingClientRect().height,
            diff: c.scrollHeight - c.clientHeight
        };
    }""")
    print("Center at 1280x650 (closed):", c650_closed)
    save_screen(page650, "43", "ui4_closed_1280x650")

    # Open settings at 650p
    page650.locator("button").filter(has_text="Settings").click()
    page650.wait_for_selector(".st-key-nc-settings")
    time.sleep(2)

    c650_open = page650.evaluate("""() => {
        const c = document.querySelector('.st-key-nc-center');
        const s = document.querySelector('.st-key-nc-settings');
        return {
            centerClientH: c.clientHeight,
            centerScrollH: c.scrollHeight,
            diff: c.scrollHeight - c.clientHeight,
            settingsClientH: s.clientHeight,
            settingsScrollH: s.scrollHeight,
        };
    }""")
    print("1280x650 (open):", c650_open)
    save_screen(page650, "44", "ui4_open_1280x650")
    page650.close()

    page.close()
    browser.close()
print("All verification steps completed successfully.")
