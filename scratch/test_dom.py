import time

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stFileUploader"]')
    time.sleep(2)
    info = page.evaluate("""() => {
        const mb = document.querySelector('[data-testid="stMainBlockContainer"]');
        const vb = mb.querySelector('[data-testid="stVerticalBlock"]');
        const vbChildren = vb ? Array.from(vb.children).map(c => {
            const inner = c.firstElementChild;
            return {
                tag: c.tagName,
                testId: c.getAttribute('data-testid'),
                className: typeof c.className === 'string' ? c.className : '',
                innerTag: inner ? inner.tagName : null,
                innerTestId: inner ? inner.getAttribute('data-testid') : null,
                innerClass: inner && typeof inner.className === 'string' ? inner.className : ''
            };
        }) : [];
        return { vbChildren: vbChildren };
    }""")
    for i, c in enumerate(info["vbChildren"]):
        print(f"vb[{i}]:", c)
    browser.close()
