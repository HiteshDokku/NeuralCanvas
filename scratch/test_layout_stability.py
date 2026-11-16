import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_img = Path("assets/samples/dog.jpg").resolve()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")
    time.sleep(1)

    get_metrics = """() => {
        const getBox = (sel) => {
            const el = document.querySelector(sel);
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return { height: Math.round(r.height), top: Math.round(r.top), bottom: Math.round(r.bottom) };
        };

        const header = getBox('.result-header-title');
        const plate = getBox('.result-plate');
        const caption = getBox('.st-key-nc-center .font-mono');
        const strip = getBox('.ref-previews-container');

        return { header, plate, caption, strip };
    }"""

    before = page.evaluate(get_metrics)

    # Upload file
    file_input = page.locator(
        '[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"]'
    )
    file_input.set_input_files(str(sample_img))
    time.sleep(2)

    after = page.evaluate(get_metrics)

    print("Before upload:", before)
    print("After upload: ", after)
    print("Identical:", before == after)
    browser.close()
