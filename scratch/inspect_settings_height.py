from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501")
    page.wait_for_selector(".st-key-nc-center")
    page.locator("button").filter(has_text="Settings").click()
    page.wait_for_selector(".st-key-nc-settings")
    info = page.evaluate("""() => {
        const s = document.querySelector('.st-key-nc-settings');
        const parent = s.parentElement;
        const grandParent = parent.parentElement;
        return {
            s: {
                rect: s.getBoundingClientRect(),
                clientHeight: s.clientHeight,
                scrollHeight: s.scrollHeight,
                inlineStyle: s.getAttribute('style'),
                computedHeight: window.getComputedStyle(s).height
            },
            parent: {
                tagName: parent.tagName,
                className: parent.className,
                rect: parent.getBoundingClientRect(),
                clientHeight: parent.clientHeight,
                computedHeight: window.getComputedStyle(parent).height
            },
            grandParent: {
                tagName: grandParent.tagName,
                className: grandParent.className,
                rect: grandParent.getBoundingClientRect(),
                clientHeight: grandParent.clientHeight
            }
        };
    }""")
    print(info)
    browser.close()
