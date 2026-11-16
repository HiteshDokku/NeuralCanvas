from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("http://localhost:8502")
    page.wait_for_selector(".st-key-nc-center")
    info = page.evaluate("""() => {
        const center = document.querySelector('.st-key-nc-center');
        const settings = document.querySelector('.st-key-nc-settings');
        const getElInfo = (el) => {
            if (!el) return null;
            return {
                tagName: el.tagName,
                className: typeof el.className === 'string' ? el.className : '',
                testId: el.getAttribute('data-testid'),
                parentTag: el.parentElement.tagName,
                parentClass: typeof el.parentElement.className === 'string' ? el.parentElement.className : '',
                parentTestId: el.parentElement.getAttribute('data-testid'),
                grandParentTag: el.parentElement.parentElement.tagName,
                grandParentClass: typeof el.parentElement.parentElement.className === 'string' ? el.parentElement.parentElement.className : '',
                grandParentTestId: el.parentElement.parentElement.getAttribute('data-testid'),
            };
        };
        return {
            center: getElInfo(center),
            settings: getElInfo(settings),
        };
    }""")
    print("center:", info["center"])
    print("settings:", info["settings"])
    browser.close()
