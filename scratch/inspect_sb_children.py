from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8505")
    page.wait_for_selector(".st-key-nc-rail-dock")
    info = page.evaluate("""() => {
        const sb = document.querySelector('[data-testid="stSidebarContent"]');
        sb.scrollTop = sb.scrollHeight - sb.clientHeight;

        const children = Array.from(sb.children).map(c => {
            const r = c.getBoundingClientRect();
            const cs = window.getComputedStyle(c);
            return {
                tag: c.tagName,
                testId: c.getAttribute('data-testid'),
                className: c.className,
                rect: r,
                paddingBottom: cs.paddingBottom,
                marginBottom: cs.marginBottom
            };
        });

        const userContent = sb.querySelector('[data-testid="stSidebarUserContent"]');
        const userContentCs = userContent ? {
            paddingBottom: window.getComputedStyle(userContent).paddingBottom,
            marginBottom: window.getComputedStyle(userContent).marginBottom,
            height: window.getComputedStyle(userContent).height,
            rect: userContent.getBoundingClientRect()
        } : null;

        return {
            sbPaddingBottom: window.getComputedStyle(sb).paddingBottom,
            children,
            userContentCs
        };
    }""")
    print("sbPaddingBottom:", info["sbPaddingBottom"])
    print("userContentCs:", info["userContentCs"])
    for c in info["children"]:
        print("child:", c)
    browser.close()
