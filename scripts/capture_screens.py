"""Drive the real app (Expo web build + real API) through all 7 required states,
check what is on screen, and save a screenshot of each plus a video walkthrough.

Prereqs: API on :8000 and `npx expo start --web` on :8081 (see README), then
    api/.venv/bin/pip install playwright
    api/.venv/bin/python scripts/capture_screens.py

Uses the installed Google Chrome (channel="chrome"); or run
`api/.venv/bin/playwright install chromium` and pass --bundled.
"""

import asyncio
import shutil
import sys
from pathlib import Path

from playwright.async_api import Page, Route, async_playwright, expect

APP_URL = "http://localhost:8081"
OUT = Path(__file__).resolve().parents[1] / "screenshots"
API_GLOB = "**/next-payment?**"


async def lookup(page: Page, phone: str) -> None:
    box = page.get_by_test_id("phone-input")
    await box.fill(phone)
    await page.get_by_test_id("check-button").click()


async def shot(page: Page, name: str) -> None:
    await page.screenshot(path=OUT / f"{name}.png", full_page=True)
    print(f"  saved screenshots/{name}.png")


async def body_text(page: Page) -> str:
    return await page.locator("body").inner_text()


async def main(bundled: bool) -> None:
    OUT.mkdir(exist_ok=True)
    video_dir = OUT / "_video"
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel=None if bundled else "chrome")
        ctx = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            record_video_dir=video_dir,
            record_video_size={"width": 390, "height": 844},
        )
        page = await ctx.new_page()
        await page.goto(APP_URL)
        await expect(page.get_by_test_id("phone-input")).to_be_visible(timeout=60_000)

        # 1. Loading — hold the real API response for 2.5 s so the spinner is visible.
        print("1 loading")
        release = asyncio.Event()

        async def slow(route: Route) -> None:
            await release.wait()
            await route.continue_()

        await page.route(API_GLOB, slow)
        await lookup(page, "9800000001")
        await expect(page.get_by_test_id("state-loading")).to_be_visible()
        assert "15000" not in await body_text(page)
        await shot(page, "1-loading")
        await page.wait_for_timeout(1500)
        release.set()
        await expect(page.get_by_test_id("state-many")).to_be_visible()
        await page.unroute(API_GLOB)

        # 2. One booking — Rohit, Kerala.
        print("2 one booking")
        await lookup(page, "9800000002")
        await expect(page.get_by_test_id("state-one")).to_be_visible()
        text = await body_text(page)
        assert "Kerala" in text and "30000" in text and "2026-11-05" in text
        await shot(page, "2-one-booking")
        await page.wait_for_timeout(1200)

        # 3. Two bookings — Asha: Bali and Goa tie on 2026-11-10, Bali wins.
        print("3 two bookings")
        await lookup(page, "9800000001")
        await expect(page.get_by_test_id("state-many")).to_be_visible()
        next_card = await page.get_by_test_id("next-card").inner_text()
        assert "Bali" in next_card and "15000" in next_card and "2026-11-10" in next_card
        assert "Goa" in await body_text(page)
        await shot(page, "3-two-bookings")
        await page.wait_for_timeout(1200)

        # 4. Overdue — Meera, Spiti, due 2026-10-15.
        print("4 overdue")
        await lookup(page, "9800000003")
        await expect(page.get_by_test_id("overdue-badge")).to_be_visible()
        assert "2026-10-15" in await page.get_by_test_id("next-card").inner_text()
        await shot(page, "4-overdue")
        await page.wait_for_timeout(1200)

        # 5. Nothing due — Neha.
        print("5 nothing due")
        await lookup(page, "9800000004")
        await expect(page.get_by_test_id("state-nothing-due")).to_be_visible()
        await shot(page, "5-nothing-due")
        await page.wait_for_timeout(1200)

        # 6. Unknown number.
        print("6 unknown number")
        await lookup(page, "9999999999")
        await expect(page.get_by_test_id("state-unknown")).to_be_visible()
        await shot(page, "6-unknown-number")
        await page.wait_for_timeout(1200)

        # 7. API down — first load real data, then make the API unreachable and
        # check again: the old amount/date must be gone, retry must be offered.
        print("7 API down")
        await lookup(page, "9800000001")
        await expect(page.get_by_test_id("state-many")).to_be_visible()
        await page.wait_for_timeout(800)
        await page.route(API_GLOB, lambda route: route.abort("connectionrefused"))
        await page.get_by_test_id("check-button").click()
        await expect(page.get_by_test_id("state-error")).to_be_visible()
        await expect(page.get_by_test_id("retry-button")).to_be_visible()
        text = await body_text(page)
        for stale in ["15000", "20000", "2026-11-10", "Bali", "Goa"]:
            assert stale not in text, f"stale value {stale!r} still on screen"
        await shot(page, "7-api-down")
        await page.wait_for_timeout(1200)

        # Retry still down -> still the error, still no data.
        await page.get_by_test_id("retry-button").click()
        await expect(page.get_by_test_id("state-error")).to_be_visible()
        assert "15000" not in await body_text(page)

        # API back -> Retry recovers.
        print("  retry after API is back")
        await page.unroute(API_GLOB)
        await page.get_by_test_id("retry-button").click()
        await expect(page.get_by_test_id("state-many")).to_be_visible()
        await page.wait_for_timeout(1500)

        video_path = await page.video.path()
        await ctx.close()
        await browser.close()

    target = OUT / "walkthrough.webm"
    shutil.move(video_path, target)
    shutil.rmtree(video_dir, ignore_errors=True)
    print(f"  saved screenshots/{target.name}")
    print("All 7 states verified.")


if __name__ == "__main__":
    asyncio.run(main(bundled="--bundled" in sys.argv))
