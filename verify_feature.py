from playwright.sync_api import Page, expect, sync_playwright

def verify_feature(page: Page):
    page.goto("http://localhost:5173")
    page.wait_for_timeout(2000)

    # Try to open an agent if needed
    try:
        page.get_by_text("Try a sample agent").click()
        page.wait_for_timeout(1000)
        page.locator("body").click() # click anywhere to close modal if exists or click a sample
        page.wait_for_timeout(1000)
    except Exception:
        pass

    page.screenshot(path="/home/jules/verification/verification.png")

if __name__ == "__main__":
    import os
    os.makedirs("/home/jules/verification/video", exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(record_video_dir="/home/jules/verification/video")
        page = context.new_page()
        try:
            verify_feature(page)
        finally:
            context.close()
            browser.close()
