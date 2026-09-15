import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000/baker"
out = sys.argv[2] if len(sys.argv) > 2 else "scripts/screenshot.png"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1000, "height": 900})
    page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))
    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    page.screenshot(path=out)
    print("saved", out)
    browser.close()
