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
        const svg = btn ? btn.querySelector('svg') : null;
        if (!svg) return { error: "no svg" };

        // Check all style sheets for rules matching svg
        const matches = [];
        for (const sheet of document.styleSheets) {
            try {
                for (const rule of sheet.cssRules) {
                    if (rule.selectorText && svg.matches(rule.selectorText)) {
                        matches.push({
                            selector: rule.selectorText,
                            display: rule.style.display,
                            cssText: rule.cssText
                        });
                    }
                }
            } catch (e) {}
        }
        return {
            svgHTML: svg.outerHTML,
            matches
        };
    }""")
    pprint.pprint(res)
    browser.close()
