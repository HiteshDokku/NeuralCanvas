from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const uploader = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"]');
        const spans = Array.from(uploader.querySelectorAll('section span, section small, section div'));
        const hintEl = spans.find(s => s.children.length === 0 && s.textContent.includes('JPG'));
        return {
            hintTag: hintEl ? hintEl.tagName : null,
            hintText: hintEl ? hintEl.textContent.trim() : null,
            hintParentTag: hintEl ? hintEl.parentElement.tagName : null,
            hintParentClass: hintEl ? hintEl.parentElement.className : null,
            csTextOverflow: hintEl ? window.getComputedStyle(hintEl).textOverflow : null
        };
    }""")
    import pprint

    pprint.pprint(res)
    browser.close()
