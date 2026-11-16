from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("http://localhost:8501")
    page.wait_for_selector('[data-testid="stSidebar"]')

    # Select "Upload custom photo" in content source
    page.locator('[data-testid="stSidebar"] [data-testid="stSelectbox"]').click()
    page.locator('li:has-text("Upload custom photo")').click()
    page.wait_for_timeout(1000)

    info = page.evaluate("""() => {
        const uploader = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"]');
        if (!uploader) return null;
        const section = uploader.querySelector('section');
        const dropzone = uploader.querySelector('[data-testid="stFileUploaderDropzone"]');
        return {
            uploaderBox: uploader.getBoundingClientRect(),
            sectionBox: section ? section.getBoundingClientRect() : null,
            dropzoneBox: dropzone ? dropzone.getBoundingClientRect() : null,
            sectionClass: section ? section.className : null,
            innerHTML: uploader.innerHTML.slice(0, 300)
        };
    }""")
    print("uploader info:", info)
    browser.close()
