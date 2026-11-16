import pprint
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_img = Path("assets/samples/dog.jpg").resolve()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    # Invalidate `section svg { display: none !important; }`
    page.evaluate("""() => {
        const style = document.createElement('style');
        style.textContent = `
            [data-testid="stSidebar"] [data-testid="stFileUploader"] section svg {
                display: block !important;
            }
            [data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] svg {
                display: block !important;
                width: 14px !important;
                height: 14px !important;
                fill: #8C8C86 !important;
            }
            [data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] button:hover svg {
                fill: #E7E5E0 !important;
            }
        `;
        document.head.appendChild(style);
    }""")

    file_input = page.locator(
        '[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"]'
    )
    file_input.set_input_files(str(sample_img))
    page.wait_for_timeout(1500)

    res = page.evaluate("""() => {
        const btn = document.querySelector('[data-testid="stFileChipDeleteBtn"] button');
        const svg = btn ? btn.querySelector('svg') : null;
        const sr = svg ? svg.getBoundingClientRect() : null;
        return {
            svgDisplay: svg ? window.getComputedStyle(svg).display : null,
            svgRect: sr,
            svgVisible: svg ? (sr.width > 0 && sr.height > 0) : false
        };
    }""")
    pprint.pprint(res)
    browser.close()
