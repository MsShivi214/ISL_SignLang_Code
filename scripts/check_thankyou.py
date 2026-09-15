from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 700, "height": 600})
    page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))

    page.goto("http://127.0.0.1:5000/avatar", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1000)

    page.fill("#text-input", "Thank you")
    page.click("button[type=submit]")
    page.wait_for_timeout(600)
    page.screenshot(path="scripts/thankyou_playback_1.png")
    page.wait_for_timeout(700)
    page.screenshot(path="scripts/thankyou_playback_2.png")
    page.wait_for_timeout(700)
    page.screenshot(path="scripts/thankyou_playback_3.png")
    page.wait_for_timeout(2000)

    gloss = page.eval_on_selector("#gloss-line", "el => el.textContent")
    missing = page.eval_on_selector("#missing-line", "el => el.textContent")
    print("gloss:", gloss, "| missing:", missing)
    browser.close()
