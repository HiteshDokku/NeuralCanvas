import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_img = Path("assets/samples/dog.jpg").resolve()

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    # Select "Upload custom photo" (which is default index 0)
    # Upload sample_img to file input
    file_input = page.locator(
        '[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"]'
    )
    file_input.set_input_files(str(sample_img))
    time.sleep(2)

    page.screenshot(path="outputs/review/debug_uploaded_chip.png")

    # Inspect DOM structure of stFileUploader
    res = page.evaluate("""() => {
        const uploader = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"]');
        if (!uploader) return { error: "not found" };

        const getTree = (el, depth = 0) => {
            if (!el || depth > 8) return null;
            const r = el.getBoundingClientRect();
            const cs = window.getComputedStyle(el);
            return {
                tag: el.tagName,
                testId: el.getAttribute('data-testid'),
                className: el.className,
                rect: { top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height },
                position: cs.position,
                display: cs.display,
                flexDirection: cs.flexDirection,
                overflow: cs.overflow,
                children: Array.from(el.children).map(c => getTree(c, depth + 1))
            };
        };

        return {
            uploaderHTML: uploader.outerHTML,
            tree: getTree(uploader)
        };
    }""")

    import json

    with open("scratch/uploader_tree.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)

    print("Wrote uploader DOM tree to scratch/uploader_tree.json")
    browser.close()
