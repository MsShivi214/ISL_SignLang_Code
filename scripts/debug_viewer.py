from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 900, "height": 700})
    page.on("console", lambda msg: print(f"[console:{msg.type}] {msg.text}") if msg.type == "error" else None)
    page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))

    page.goto("http://127.0.0.1:5000/avatar", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)
    page.screenshot(path="scripts/viewer_before.png")

    page.fill("#text-input", "Please sorry hello")
    page.click("button[type=submit]")

    for _ in range(30):
        page.wait_for_timeout(1000)
        status = page.eval_on_selector("#status", "el => el.textContent")
        if status == "":
            break
    print("final status:", repr(status))
    print("gloss:", page.eval_on_selector("#gloss-line", "el => el.textContent"))
    print("missing:", page.eval_on_selector("#missing-line", "el => el.textContent"))
    page.screenshot(path="scripts/viewer_after.png")
    browser.close()
