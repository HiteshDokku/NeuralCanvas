from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8505")
    page.wait_for_selector(".st-key-nc-rail-dock")
    info = page.evaluate("""() => {
        const sb = document.querySelector('[data-testid="stSidebarContent"]');
        const vb = sb.querySelector('[data-testid="stVerticalBlock"]');
        const c = document.querySelector('.st-key-nc-rail-content');
        const d = document.querySelector('.st-key-nc-rail-dock');
        const dWrap = d.closest('[data-testid="stLayoutWrapper"]') || d;

        sb.scrollTop = sb.scrollHeight - sb.clientHeight;

        return {
            sbScrollTop: sb.scrollTop,
            sbScrollHeight: sb.scrollHeight,
            sbClientHeight: sb.clientHeight,
            sbRect: sb.getBoundingClientRect(),
            vbRect: vb.getBoundingClientRect(),
            cRect: c.getBoundingClientRect(),
            dWrapRect: dWrap.getBoundingClientRect(),
            dRect: d.getBoundingClientRect(),
            dockCs: {
                position: window.getComputedStyle(dWrap).position,
                bottom: window.getComputedStyle(dWrap).bottom,
            }
        };
    }""")
    print("sb:", info["sbScrollTop"], info["sbScrollHeight"], info["sbClientHeight"])
    print("sbRect:", info["sbRect"])
    print("vbRect:", info["vbRect"])
    print("cRect:", info["cRect"])
    print("dWrapRect:", info["dWrapRect"])
    print("dockCs:", info["dockCs"])
    browser.close()
