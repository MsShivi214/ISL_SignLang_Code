import sys

from playwright.sync_api import sync_playwright

name = sys.argv[1] if len(sys.argv) > 1 else "Namaste"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1000, "height": 900})
    page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))

    page.goto("http://127.0.0.1:5000/baker", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1000)
    page.select_option("#video-select", label=name)
    page.wait_for_timeout(500)
    page.click("#bake-button")

    status = None
    for _ in range(60):
        page.wait_for_timeout(2000)
        status = page.eval_on_selector("#status", "el => el.textContent")
        if status == "Done." or (status and status.startswith("Error")):
            break

    log = page.eval_on_selector("#log", "el => el.textContent")
    print(log)
    page.screenshot(path=f"scripts/{name.lower()}_bake_check.png")

    if status != "Done.":
        print(f"SKIP saving {name}: status={status}")
    else:
        page.fill("#sign-name", name)
        page.click("#save-button")
        page.wait_for_timeout(1000)
        print("save status:", page.eval_on_selector("#status", "el => el.textContent"))

    browser.close()
