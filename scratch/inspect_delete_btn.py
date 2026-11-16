import pprint
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_img = Path("assets/samples/dog.jpg").resolve()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    file_input = page.locator(
        '[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"]'
    )
    file_input.set_input_files(str(sample_img))
    page.wait_for_timeout(1500)

    res = page.evaluate("""() => {
        const btn = document.querySelector('[data-testid="stFileChipDeleteBtn"] button');
        if (!btn) return { error: "no btn" };
        const svg = btn.querySelector('svg');
        const icon = btn.querySelector('[data-testid="stIconMaterial"]');

        const getInfo = (el) => {
            if (!el) return null;
            const cs = window.getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return {
                tag: el.tagName,
                outerHTML: el.outerHTML,
                rect: { top: r.top, bottom: r.bottom, width: r.width, height: r.height },
                display: cs.display,
                width: cs.width,
                height: cs.height,
                fill: cs.fill,
                color: cs.color,
                visibility: cs.visibility
            };
        };

        return {
            btnHTML: btn.outerHTML,
            svg: getInfo(svg),
            icon: getInfo(icon)
        };
    }""")
    pprint.pprint(res)
    browser.close()
