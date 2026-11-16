import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sample_img = Path("assets/samples/dog.jpg").resolve()

selectors = [
    '[data-testid="stSidebar"] [data-testid="stFileUploader"] section:not(:has([data-testid="stFileChips"]))',
    '[data-testid="stSidebar"] [data-testid="stFileUploader"] section:has([data-testid="stFileChips"])',
    '[data-testid="stSidebar"] [data-testid="stFileUploader"] section:has([data-testid="stFileChips"]) > div',
    '[data-testid="stSidebar"] [data-testid="stFileChips"]',
    '[data-testid="stSidebar"] [data-testid="stFileChips"] > div',
    '[data-testid="stSidebar"] [data-testid="stFileChip"]',
    '[data-testid="stSidebar"] [data-testid="stFileChip"] > div:first-child',
    '[data-testid="stSidebar"] [data-testid="stFileChip"] > div:first-child svg',
    '[data-testid="stSidebar"] [data-testid="stFileChip"] > div:nth-child(2)',
    '[data-testid="stSidebar"] [data-testid="stFileChip"] [data-testid="stFileChipName"]',
    '[data-testid="stSidebar"] [data-testid="stFileChip"] > div:nth-child(2) > div:last-child',
    '[data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"]',
    '[data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] button',
    '[data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] svg',
    '[data-testid="stSidebar"] [data-testid="stFileChipDeleteBtn"] [data-testid="stIconMaterial"]',
    '[data-testid="stSidebar"] [data-testid="stFileUploader"] button[data-testid="stBaseButton-borderlessIcon"]',
    ".sidebar-device-line",
    '[data-testid="stSidebar"] [data-testid="stVerticalBlock"].st-key-nc-rail-dock',
    ".st-key-nc-rail-dock",
    '.st-key-nc-rail-dock [data-testid="stElementContainer"]',
    '.st-key-nc-rail-dock [data-testid="stMarkdownContainer"]',
    ".st-key-nc-rail-dock button",
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    page.goto("http://localhost:8501", wait_until="networkidle")
    page.wait_for_selector(".st-key-nc-rail-dock")

    # Count before upload
    before_counts = {}
    for sel in selectors:
        before_counts[sel] = page.locator(sel).count()

    # Upload
    file_input = page.locator(
        '[data-testid="stSidebar"] [data-testid="stFileUploader"] input[type="file"]'
    )
    file_input.set_input_files(str(sample_img))
    time.sleep(2)

    # Count after upload
    after_counts = {}
    for sel in selectors:
        after_counts[sel] = page.locator(sel).count()

    print("| Selector | Match Count (Empty) | Match Count (Uploaded) | Purpose |")
    print("| :--- | :---: | :---: | :--- |")
    for sel in selectors:
        c1 = before_counts[sel]
        c2 = after_counts[sel]
        print(f"| `{sel}` | {c1} | {c2} | |")

    browser.close()
