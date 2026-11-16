from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    res = page.evaluate("""() => {
        const uploader = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"]');
        if (!uploader) return { error: "No uploader found" };
        const allText = Array.from(uploader.querySelectorAll('*')).map(el => ({
            tag: el.tagName,
            text: el.textContent.trim(),
            className: el.className,
            title: el.getAttribute('title')
        }));
        return {
            innerHTML: uploader.innerHTML,
            allText: allText.filter(t => t.text.length > 0 && t.text.length < 50)
        };
    }""")
    import pprint

    pprint.pprint(res["allText"])
    browser.close()
