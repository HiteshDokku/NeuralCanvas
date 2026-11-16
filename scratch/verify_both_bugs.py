import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_img = Path("assets/samples/dog.jpg").resolve()
output_dir = Path("outputs/review")
output_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()

    # Test two viewports: 1366x768 and 1024x768 (narrower width)
    for w, h in [(1366, 768), (1024, 768)]:
        tag = f"{w}x{h}"
        page = browser.new_page(viewport={"width": w, "height": h})
        page.goto("http://localhost:8501", wait_until="networkidle")
        page.wait_for_selector(".st-key-nc-rail-dock")
        time.sleep(1)

        # Before upload measurements
        before = page.evaluate("""() => {
            const getBox = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height };
            };

            return {
                header: getBox('.result-header-title'),
                plate: getBox('.result-plate'),
                caption: getBox('.st-key-nc-center .font-mono'),
                strip: getBox('.ref-previews-container'),
                dropzone: getBox('[data-testid="stSidebar"] [data-testid="stFileUploader"] section'),
                devLine: getBox('.sidebar-device-line'),
                btn: getBox('.st-key-btn_stylize button') || getBox('[data-testid="stBaseButton-primary"]'),
                dock: getBox('.st-key-nc-rail-dock')
            };
        }""")

        # Screenshot before upload
        page.screenshot(path=str(output_dir / f"ui6_full_before_upload_{tag}.png"))

        # Stylize footer screenshot
        dock_loc = page.locator('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
        if dock_loc.count() > 0:
            dock_loc.first.screenshot(path=str(output_dir / f"ui6_stylize_footer_{tag}.png"))

        # Perform Upload with real file input
        file_input = page.locator(
            '[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"]'
        )
        file_input.set_input_files(str(sample_img))
        time.sleep(2)

        # Screenshot after upload
        page.screenshot(path=str(output_dir / f"ui6_full_after_upload_{tag}.png"))

        # After upload measurements
        after = page.evaluate("""() => {
            const getBox = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height };
            };

            const dz = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"] section');
            const chip = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileChip"]');
            const addBtn = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"] button[data-testid="stBaseButton-borderlessIcon"]');
            const deleteBtn = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] button');
            const deleteSvg = deleteBtn ? deleteBtn.querySelector('svg') : null;
            const deleteIcon = deleteBtn ? deleteBtn.querySelector('[data-testid="stIconMaterial"]') : null;
            const chipName = chip ? chip.querySelector('[data-testid="stFileChipName"]') : null;

            const devLine = document.querySelector('.sidebar-device-line');
            const btn = document.querySelector('.st-key-btn_stylize button') || document.querySelector('[data-testid="stBaseButton-primary"]');
            const dock = document.querySelector('[data-testid="stLayoutWrapper"]:has(> .st-key-nc-rail-dock)')
                || document.querySelector('.st-key-nc-rail-dock');

            const cr = chip ? chip.getBoundingClientRect() : null;
            const ar = addBtn ? addBtn.getBoundingClientRect() : null;
            const dr = deleteBtn ? deleteBtn.getBoundingClientRect() : null;
            const sr = deleteSvg ? deleteSvg.getBoundingClientRect() : (deleteIcon ? deleteIcon.getBoundingClientRect() : null);
            const dlr = devLine ? devLine.getBoundingClientRect() : null;
            const br = btn ? btn.getBoundingClientRect() : null;
            const dkr = dock ? dock.getBoundingClientRect() : null;

            const dzStyle = dz ? window.getComputedStyle(dz) : null;
            const dzBorder = dzStyle ? `${dzStyle.borderWidth} ${dzStyle.borderStyle} ${dzStyle.borderColor}` : null;
            const dzRect = dz ? dz.getBoundingClientRect() : null;

            return {
                header: getBox('.result-header-title'),
                plate: getBox('.result-plate'),
                caption: getBox('.st-key-nc-center .font-mono'),
                strip: getBox('.ref-previews-container'),
                dropzoneRect: dzRect,
                dropzoneBorder: dzBorder,
                hasDashedBorder: dzStyle ? (dzStyle.borderStyle.includes('dashed')) : false,
                chipRect: cr,
                addBtnRect: ar,
                deleteBtnRect: dr,
                iconRect: sr,
                iconWidth: sr ? sr.width : 0,
                iconHeight: sr ? sr.height : 0,
                iconRendered: sr ? (sr.width > 0 && sr.height > 0) : false,
                chipNameTextOverflow: chipName ? window.getComputedStyle(chipName).textOverflow : null,
                gapChipToAddBtn: (cr && ar) ? Math.round(ar.top - cr.bottom) : null,
                devLineRect: dlr,
                btnRect: br,
                devLineEndsAboveBtn: (dlr && br) ? (dlr.bottom <= br.top) : false,
                gapDevLineToBtn: (dlr && br) ? Math.round(br.top - dlr.bottom) : null,
                dockBottom: dkr ? dkr.bottom : null,
                diffFromVh: dkr ? Math.round(window.innerHeight - dkr.bottom) : null
            };
        }""")

        print(f"\n=================== VIEWPORT {tag} ===================")
        print("--- BUG 1: File Chip Measurements ---")
        print("Dropzone Border when uploaded:", after["dropzoneBorder"])
        print("Has Dashed Border:", after["hasDashedBorder"])
        print("Chip Rect:", after["chipRect"])
        print("Add Button Rect:", after["addBtnRect"])
        print("Gap Chip to Add Button:", after["gapChipToAddBtn"], "px")
        print("Remove Icon Width:", after["iconWidth"], "px, Height:", after["iconHeight"], "px")
        print("Remove Icon Rendered:", after["iconRendered"])
        print("Chip Name Text-Overflow:", after["chipNameTextOverflow"])

        print("\n--- BUG 2: Stylize Dock Measurements ---")
        print("DevLine Rect:", after["devLineRect"])
        print("Btn Rect:", after["btnRect"])
        print("DevLine Ends Above Button:", after["devLineEndsAboveBtn"])
        print("Gap DevLine to Button:", after["gapDevLineToBtn"], "px")
        print("Dock Bottom:", after["dockBottom"], "px, Diff from VH:", after["diffFromVh"], "px")

        print("\n--- Layout Stability (Before vs After Upload) ---")
        for key in ["header", "plate", "caption", "strip"]:
            bh = before[key]["height"] if before[key] else None
            ah = after[key]["height"] if after[key] else None
            print(f"{key.capitalize()} height: before={bh}, after={ah}, identical={bh == ah}")

        page.close()

    browser.close()
