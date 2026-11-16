import pprint
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_img = Path("assets/samples/dog.jpg").resolve()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    # Inspect without our overrides
    file_input = page.locator(
        '[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"]'
    )
    file_input.set_input_files(str(sample_img))
    page.wait_for_timeout(1500)

    res = page.evaluate("""() => {
        const uploader = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"]');
        const section = uploader.querySelector('section');
        const chips = uploader.querySelector('[data-testid="stFileChips"]');
        const chip = uploader.querySelector('[data-testid="stFileChip"]');
        const addBtn = uploader.querySelector('[data-testid="stBaseButton-borderlessIcon"]');

        return {
            uploaderHTML: uploader.outerHTML,
            sectionClass: section ? section.className : null,
            chipsClass: chips ? chips.className : null,
            chipClass: chip ? chip.className : null,
            addBtnClass: addBtn ? addBtn.className : null
        };
    }""")
    pprint.pprint(res)
    browser.close()
