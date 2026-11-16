import pprint
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_img = Path("assets/samples/dog.jpg").resolve()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    # 1. State Before Upload
    before_state = page.evaluate("""() => {
        const uploader = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"]');
        const dz = uploader.querySelector('[data-testid="stFileUploaderDropzone"]');
        const dzRect = dz.getBoundingClientRect();
        return {
            dzHTML: dz.outerHTML,
            dzRect: { top: dzRect.top, bottom: dzRect.bottom, width: dzRect.width, height: dzRect.height }
        };
    }""")
    print("=== BEFORE UPLOAD ===")
    pprint.pprint(before_state)

    # 2. Upload file
    file_input = page.locator(
        '[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"]'
    )
    file_input.set_input_files(str(sample_img))
    time.sleep(1.5)

    # 3. State After Upload
    after_state = page.evaluate("""() => {
        const uploader = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"]');
        const dz = uploader.querySelector('[data-testid="stFileUploaderDropzone"]');
        const chips = uploader.querySelector('[data-testid="stFileChips"]');
        const chip = uploader.querySelector('[data-testid="stFileChip"]');
        const addBtn = uploader.querySelector('button[aria-label="Add files"]') || uploader.querySelector('[data-testid="stBaseButton-borderlessIcon"]');
        const deleteBtn = uploader.querySelector('[data-testid="stFileChipDeleteBtn"] button') || uploader.querySelector('[data-testid="stFileChipDeleteBtn"]');

        const getR = (el) => {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            const cs = window.getComputedStyle(el);
            return {
                tag: el.tagName,
                className: el.className,
                rect: { top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height },
                display: cs.display,
                position: cs.position,
                margin: cs.margin,
                padding: cs.padding,
                border: cs.border,
                maxHeight: cs.maxHeight,
                height: cs.height
            };
        };

        return {
            dz: getR(dz),
            chips: getR(chips),
            chip: getR(chip),
            addBtn: getR(addBtn),
            deleteBtn: getR(deleteBtn),
            chipInner: chip ? Array.from(chip.children).map(getR) : []
        };
    }""")
    print("\n=== AFTER UPLOAD ===")
    pprint.pprint(after_state)

    browser.close()
