import shutil
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

long_img = Path("assets/samples/Hitesh College Campus Photo 2026 Very Long Filename.jpg")
shutil.copy("assets/samples/dog.jpg", long_img)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    file_input = page.locator(
        '[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"]'
    )
    file_input.set_input_files(str(long_img.resolve()))
    time.sleep(2)

    page.screenshot(path="outputs/review/ui6_long_filename_chip.png")

    res = page.evaluate("""() => {
        const chip = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileChip"]');
        const nameEl = chip ? chip.querySelector('[data-testid="stFileChipName"]') : null;
        const thumb = chip ? chip.querySelector(':scope > div:first-child') : null;
        const delBtn = chip ? chip.querySelector('[data-testid="stFileChipDeleteBtn"]') : null;
        const addBtn = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"] button[data-testid="stBaseButton-borderlessIcon"]');

        const r = (el) => el ? el.getBoundingClientRect() : null;

        return {
            chipRect: r(chip),
            thumbRect: r(thumb),
            nameRect: r(nameEl),
            delBtnRect: r(delBtn),
            addBtnRect: r(addBtn),
            nameOverflow: nameEl ? window.getComputedStyle(nameEl).overflow : null,
            nameTextOverflow: nameEl ? window.getComputedStyle(nameEl).textOverflow : null,
            nameWhiteSpace: nameEl ? window.getComputedStyle(nameEl).whiteSpace : null,
            delBtnInsideChip: (chip && delBtn) ? (delBtn.getBoundingClientRect().right <= chip.getBoundingClientRect().right + 1) : false,
            gapChipToAdd: (chip && addBtn) ? (addBtn.getBoundingClientRect().top - chip.getBoundingClientRect().bottom) : null
        };
    }""")

    import pprint

    pprint.pprint(res)
    browser.close()

if long_img.exists():
    long_img.unlink()
