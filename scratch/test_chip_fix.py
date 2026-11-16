import pprint
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_img = Path("assets/samples/dog.jpg").resolve()

test_css = """
/* Empty Dropzone */
[data-testid="stSidebar"] [data-testid="stFileUploader"] section:not(:has([data-testid="stFileChips"])) {
    padding: 4px 8px !important;
    min-height: 36px !important;
    height: auto !important;
    max-height: 48px !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    gap: 8px !important;
    background-color: #131313 !important;
    border: 1px dashed #3A3A3A !important;
    border-radius: 2px !important;
}

/* Uploaded State: Replace dropzone with normal-flow container */
[data-testid="stSidebar"] [data-testid="stFileUploader"] section:has([data-testid="stFileChips"]) {
    padding: 0 !important;
    min-height: 0 !important;
    height: auto !important;
    max-height: none !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    background: transparent !important;
    border: none !important;
    gap: 8px !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] section:has([data-testid="stFileChips"]) > div {
    display: flex !important;
    flex-direction: column !important;
    align-items: stretch !important;
    gap: 8px !important;
    width: 100% !important;
}

/* File Chips */
[data-testid="stSidebar"] [data-testid="stFileChips"] {
    display: flex !important;
    flex-direction: column !important;
    gap: 4px !important;
    width: 100% !important;
    height: auto !important;
}

[data-testid="stSidebar"] [data-testid="stFileChips"] > div,
[data-testid="stSidebar"] [data-testid="stFileChips"] > div > div {
    width: 100% !important;
    height: auto !important;
    overflow: visible !important;
}

/* File Chip: flex row (thumbnail | name+size | remove) */
[data-testid="stSidebar"] [data-testid="stFileChip"] {
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    width: 100% !important;
    height: 40px !important;
    min-height: 40px !important;
    max-height: 40px !important;
    padding: 4px 8px !important;
    background-color: #1A1A1A !important;
    border: 1px solid #2A2A2A !important;
    border-radius: 2px !important;
    box-sizing: border-box !important;
    gap: 8px !important;
}

/* Thumbnail */
[data-testid="stSidebar"] [data-testid="stFileChip"] > div:first-child {
    flex: 0 0 28px !important;
    width: 28px !important;
    height: 28px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background-color: #262626 !important;
    border-radius: 2px !important;
    overflow: hidden !important;
}

[data-testid="stSidebar"] [data-testid="stFileChip"] > div:first-child svg {
    display: block !important;
    width: 16px !important;
    height: 16px !important;
    fill: #8C8C86 !important;
}

/* Name + Size */
[data-testid="stSidebar"] [data-testid="stFileChip"] > div:nth-child(2) {
    flex: 1 1 auto !important;
    min-width: 0 !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    gap: 1px !important;
    overflow: hidden !important;
}

[data-testid="stSidebar"] [data-testid="stFileChip"] [data-testid="stFileChipName"] {
    font-family: "IBM Plex Sans", sans-serif !important;
    font-size: 12px !important;
    color: #E7E5E0 !important;
    line-height: 1.3 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    min-width: 0 !important;
    display: block !important;
}

[data-testid="stSidebar"] [data-testid="stFileChip"] > div:nth-child(2) > div:last-child {
    font-family: "IBM Plex Mono", monospace !important;
    font-size: 11px !important;
    color: #8C8C86 !important;
    line-height: 1.2 !important;
    white-space: nowrap !important;
}

/* Remove button */
[data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] {
    flex: 0 0 24px !important;
    width: 24px !important;
    height: 24px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0 !important;
    padding: 0 !important;
}

[data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] button {
    width: 24px !important;
    height: 24px !important;
    min-height: 24px !important;
    max-height: 24px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background-color: transparent !important;
    border: none !important;
    border-radius: 2px !important;
    color: #8C8C86 !important;
    cursor: pointer !important;
    transition: background-color 100ms ease, color 100ms ease !important;
}

[data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] button:hover {
    background-color: #262626 !important;
    color: #E7E5E0 !important;
}

[data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] svg {
    display: block !important;
    width: 14px !important;
    height: 14px !important;
    fill: currentColor !important;
    color: inherit !important;
}

[data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] [data-testid="stIconMaterial"] {
    display: inline-block !important;
    font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
    font-size: 14px !important;
    color: inherit !important;
}

/* Add Button ("+") */
[data-testid="stSidebar"] [data-testid="stFileUploader"] button[data-testid="stBaseButton-borderlessIcon"] {
    align-self: flex-start !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    height: 26px !important;
    min-height: 26px !important;
    padding: 2px 8px !important;
    background-color: #1A1A1A !important;
    border: 1px solid #2A2A2A !important;
    border-radius: 2px !important;
    color: #8C8C86 !important;
    margin: 0 !important;
    transition: background-color 100ms ease, border-color 100ms ease, color 100ms ease !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button[data-testid="stBaseButton-borderlessIcon"]:hover {
    background-color: #262626 !important;
    border-color: #3A3A3A !important;
    color: #E7E5E0 !important;
}

[data-testid="stSidebar"] [data-testid="stFileUploader"] button[data-testid="stBaseButton-borderlessIcon"] [data-testid="stIconMaterial"] {
    font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
    font-size: 16px !important;
    color: inherit !important;
    display: inline-block !important;
}
"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    # Invalidate theme.css rule line 322 by overriding with highest specificity
    page.evaluate(f"""() => {{
        const style = document.createElement('style');
        style.textContent = `
            [data-testid="stSidebar"] [data-testid="stFileUploader"] section svg {{
                display: initial;
            }}
            {test_css}
        `;
        document.head.appendChild(style);
    }}""")

    file_input = page.locator(
        '[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"]'
    )
    file_input.set_input_files(str(sample_img))
    page.wait_for_timeout(1500)

    page.screenshot(path="outputs/review/test_chip_after_fix.png")

    res = page.evaluate("""() => {
        const uploader = document.querySelector('[data-testid="stSidebar"] [data-testid="stFileUploader"]');
        const dz = uploader.querySelector('[data-testid="stFileUploaderDropzone"]');
        const chip = uploader.querySelector('[data-testid="stFileChip"]');
        const addBtn = uploader.querySelector('button[aria-label="Add files"]') || uploader.querySelector('[data-testid="stBaseButton-borderlessIcon"]');
        const deleteBtn = uploader.querySelector('[data-testid="stFileChipDeleteBtn"] button');
        const deleteSvg = deleteBtn ? deleteBtn.querySelector('svg') : null;
        const deleteIcon = deleteBtn ? deleteBtn.querySelector('[data-testid="stIconMaterial"]') : null;

        const cr = chip.getBoundingClientRect();
        const ar = addBtn.getBoundingClientRect();
        const dr = deleteBtn.getBoundingClientRect();
        const sr = deleteSvg ? deleteSvg.getBoundingClientRect() : (deleteIcon ? deleteIcon.getBoundingClientRect() : null);
        const dzr = dz.getBoundingClientRect();

        return {
            dzRect: dzr,
            dzBorder: window.getComputedStyle(dz).border,
            chipRect: cr,
            addBtnRect: ar,
            gapChipToAddBtn: Math.round(ar.top - cr.bottom),
            deleteBtnRect: dr,
            iconRect: sr,
            iconRendered: sr ? (sr.width > 0 && sr.height > 0) : false
        };
    }""")
    pprint.pprint(res)
    browser.close()
