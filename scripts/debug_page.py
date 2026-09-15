import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000/baker"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()

    page.on("console", lambda msg: print(f"[console:{msg.type}] {msg.text}"))
    page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))
    page.on("requestfailed", lambda req: print(f"[requestfailed] {req.url} - {req.failure}"))
    page.on("response", lambda res: print(f"[response] {res.status} {res.url}") if res.status >= 400 else None)

    page.goto(url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(4000)

    select_options = page.eval_on_selector_all("#video-select option", "els => els.map(e => e.textContent)")
    print("video-select options:", select_options)

    browser.close()
