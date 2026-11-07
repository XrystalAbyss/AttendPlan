"""Script to inspect UX across multiple viewports and capture baseline screenshots.

Viewports tested:
- 1366x768 (Standard laptop)
- 1920x1080 (Full HD desktop)
- 1440x900 (Widescreen laptop)
- 768x1024 (Tablet portrait)
- 390x844 (Mobile portrait)
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

OUTPUT_DIR = Path(__file__).resolve().parents[2] / "reports" / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    {"name": "1366x768_laptop", "width": 1366, "height": 768},
    {"name": "1920x1080_desktop", "width": 1920, "height": 1080},
    {"name": "1440x900_macbook", "width": 1440, "height": 900},
    {"name": "768x1024_tablet", "width": 768, "height": 1024},
    {"name": "390x844_mobile", "width": 390, "height": 844},
]

async def capture_all_views():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for vp in VIEWPORTS:
            context = await browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                device_scale_factor=1,
            )
            page = await context.new_page()

            # Enforce strictly offline loopback
            async def route_handler(route):
                req_url = route.request.url
                if "127.0.0.1" in req_url or "localhost" in req_url:
                    await route.continue_()
                else:
                    await route.abort()

            await page.route("**/*", route_handler)

            # Navigate to local dashboard
            await page.goto("http://127.0.0.1:5173", wait_until="networkidle")
            await page.wait_for_timeout(1000)

            # 1. Home View
            await page.screenshot(path=str(OUTPUT_DIR / f"{vp['name']}_01_home.png"), full_page=False)

            # 2. Attendance View (Roster)
            await page.click("button:has-text('Attendance')")
            await page.wait_for_timeout(600)
            await page.screenshot(path=str(OUTPUT_DIR / f"{vp['name']}_02_attendance_roster.png"), full_page=False)

            # 3. Attendance View (Calendar)
            calendar_btn = page.locator("button:has-text('Date-wise Calendar')")
            if await calendar_btn.count() > 0:
                await calendar_btn.first.click()
                await page.wait_for_timeout(800)
                await page.screenshot(path=str(OUTPUT_DIR / f"{vp['name']}_03_attendance_calendar.png"), full_page=False)

            # 4. Performance View
            await page.click("button:has-text('Performance')")
            await page.wait_for_timeout(800)
            await page.screenshot(path=str(OUTPUT_DIR / f"{vp['name']}_04_performance.png"), full_page=False)

            # 5. Settings View
            await page.click("button:has-text('Settings')")
            await page.wait_for_timeout(600)
            await page.screenshot(path=str(OUTPUT_DIR / f"{vp['name']}_05_settings.png"), full_page=False)

            # 6. Simulator Drawer (from Attendance)
            await page.click("button:has-text('Attendance')")
            await page.wait_for_timeout(500)
            sim_buttons = page.locator("button[title*='Simulate attendance']")
            if await sim_buttons.count() > 0:
                await sim_buttons.first.click()
                await page.wait_for_timeout(600)
                await page.screenshot(path=str(OUTPUT_DIR / f"{vp['name']}_06_simulator.png"), full_page=False)
                # Close simulator
                close_sim = page.locator("button:has-text('Close Simulator')")
                if await close_sim.count() > 0:
                    await close_sim.first.click()
                    await page.wait_for_timeout(300)

            await context.close()

        await browser.close()
        print(f"Screenshots captured successfully in {OUTPUT_DIR}")

if __name__ == "__main__":
    asyncio.run(capture_all_views())

