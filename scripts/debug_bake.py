from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1000, "height": 900})

    page.on("console", lambda msg: print(f"[console:{msg.type}] {msg.text}"))
    page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))
    page.on("requestfailed", lambda req: print(f"[requestfailed] {req.url} - {req.failure}"))

    page.goto("http://127.0.0.1:5000/baker", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(1500)

    # pick "Sorry" which had the best hand-tracking in the earlier feasibility test
    page.select_option("#video-select", label="Sorry")
    page.wait_for_timeout(500)

    print("clicking Start baking...")
    page.click("#bake-button")

    # baking runs frame-by-frame; give it generous time and poll progress,
    # grabbing a mid-bake screenshot so we can see actual signing motion
    # rather than just the (often near-rest) final frame.
    shots_taken = set()
    checkpoints = [25, 50, 75]
    for _ in range(60):
        page.wait_for_timeout(2000)
        progress = page.eval_on_selector("#bake-progress", "el => el.value")
        status = page.eval_on_selector("#status", "el => el.textContent")
        print(f"progress={progress} status={status}")
        for cp in checkpoints:
            if cp not in shots_taken and progress and progress >= cp:
                page.screenshot(path=f"scripts/bake_{cp}.png")
                shots_taken.add(cp)
        if status == "Done." or (status and status.startswith("Error")):
            break

    log = page.eval_on_selector("#log", "el => el.textContent")
    print("LOG:\n", log)

    page.screenshot(path="scripts/bake_result.png")
    browser.close()
