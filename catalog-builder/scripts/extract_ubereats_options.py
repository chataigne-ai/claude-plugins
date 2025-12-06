#!/usr/bin/env python3
"""
Extract product customization options from Uber Eats using Playwright.

This script opens an Uber Eats store page, clicks on products, and captures
the API responses that contain the full customization/options data.

Usage:
    python extract_ubereats_options.py <store_url> [output_dir]

Requirements:
    pip install playwright
    playwright install chromium

Example:
    python extract_ubereats_options.py \
        "https://www.ubereats.com/fr-en/store/chamas-tacos-strasbourg/_YQl0pTOWUymxYroUtEmWA" \
        /tmp/chamas_options
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright

# Default configuration
DEFAULT_OUTPUT_DIR = "/tmp/ubereats_options"
MAX_ITEMS_TO_CLICK = 100  # Set to None for all items
WAIT_AFTER_CLICK = 2.0  # Seconds to wait after clicking each item
BROWSER_TIMEOUT = 60000  # 60 seconds


async def extract_options(store_url: str, output_dir: str):
    """
    Extract customization options from an Uber Eats store.

    The script captures API responses when products are clicked, which contain
    the full customization data including:
    - Option groups (e.g., "Taille au choix", "Sauces")
    - Individual options with prices
    - Nested customizations (e.g., size -> meat choices)
    - Min/max selections for each group
    """

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        # Launch visible browser (headless=False) to see progress
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            viewport={"width": 1400, "height": 900},
            locale="fr-FR"
        )

        # Track captured API responses
        captured_responses = []
        response_count = 0

        async def handle_response(response):
            """Capture API responses that contain item customization data."""
            nonlocal response_count
            url = response.url

            # Look for API endpoints that return item data
            if any(x in url for x in ["eats.api", "getMenuItemV1", "getStoreV1", "/item/"]):
                try:
                    body = await response.body()
                    if len(body) > 1000:  # Skip tiny responses
                        response_count += 1
                        filepath = os.path.join(output_dir, f"response_{response_count:03d}.json")

                        with open(filepath, "wb") as f:
                            f.write(body)

                        captured_responses.append({
                            "file": filepath,
                            "url": url[:100],
                            "size": len(body)
                        })
                        print(f"  📥 Captured response #{response_count}: {len(body)} bytes")
                except Exception as e:
                    pass

        page = await context.new_page()
        page.on("response", handle_response)

        # Use PICKUP mode to avoid address requirements
        if "diningMode=" not in store_url:
            store_url += "?diningMode=PICKUP"
        elif "diningMode=DELIVERY" in store_url:
            store_url = store_url.replace("diningMode=DELIVERY", "diningMode=PICKUP")

        print(f"🌐 Opening: {store_url}")
        await page.goto(store_url, timeout=BROWSER_TIMEOUT)
        await asyncio.sleep(3)

        # Accept cookies if present
        try:
            cookie_btn = await page.query_selector('button:has-text("Accept"), button:has-text("Accepter")')
            if cookie_btn:
                await cookie_btn.click()
                print("🍪 Accepted cookies")
                await asyncio.sleep(1)
        except:
            pass

        # Wait for menu to fully load
        print("⏳ Waiting for menu to load...")
        await asyncio.sleep(5)

        # Take screenshot for reference
        screenshot_path = os.path.join(output_dir, "page_screenshot.png")
        await page.screenshot(path=screenshot_path)
        print(f"📸 Saved screenshot: {screenshot_path}")

        # Find all menu items (products with prices)
        menu_items = await page.query_selector_all('li')
        clickable_items = []

        for item in menu_items:
            try:
                text = await item.inner_text()
                # Products typically have € in their text
                if "€" in text and len(text) > 5:
                    clickable_items.append((item, text.split("\n")[0][:50]))
            except:
                pass

        print(f"🍽️  Found {len(clickable_items)} menu items with prices")

        # Limit items if configured
        items_to_process = clickable_items
        if MAX_ITEMS_TO_CLICK:
            items_to_process = clickable_items[:MAX_ITEMS_TO_CLICK]

        # Click each item to trigger API calls for customization data
        products_processed = []

        for i, (item, name) in enumerate(items_to_process):
            try:
                print(f"\n[{i+1}/{len(items_to_process)}] 👆 Clicking: {name}")

                # Click the item
                await item.click()
                await asyncio.sleep(WAIT_AFTER_CLICK)

                # Check if modal opened
                modal = await page.query_selector('[role="dialog"], [data-testid*="modal"]')
                if modal:
                    products_processed.append(name)
                    print(f"  ✅ Modal opened for: {name}")

                    # Close modal
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.5)
                else:
                    print(f"  ⚠️  No modal opened")

            except Exception as e:
                print(f"  ❌ Error: {str(e)[:50]}")
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)

        # Save summary
        summary = {
            "store_url": store_url,
            "products_clicked": products_processed,
            "responses_captured": captured_responses,
            "total_products": len(products_processed),
            "total_responses": len(captured_responses)
        }

        summary_path = os.path.join(output_dir, "extraction_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        print(f"\n\n{'='*50}")
        print(f"✅ EXTRACTION COMPLETE")
        print(f"{'='*50}")
        print(f"📁 Output directory: {output_dir}")
        print(f"🍽️  Products clicked: {len(products_processed)}")
        print(f"📥 API responses captured: {len(captured_responses)}")
        print(f"📋 Summary saved: {summary_path}")

        # Keep browser open briefly for inspection
        print("\n⏳ Browser closing in 10 seconds...")
        await asyncio.sleep(10)

        await browser.close()

    return summary


def parse_responses(output_dir: str) -> dict:
    """
    Parse all captured responses to extract customization options.

    Returns a dict mapping product names to their customization groups.
    """
    import glob

    all_customizations = {}

    for filepath in sorted(glob.glob(os.path.join(output_dir, "response_*.json"))):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            if 'data' not in data:
                continue

            item_data = data['data']
            product_title = item_data.get('title', item_data.get('itemTitle', 'Unknown'))

            if 'customizationsList' in item_data and item_data['customizationsList']:
                customizations = []

                for cust_group in item_data['customizationsList']:
                    group = {
                        "title": cust_group.get('title', 'Unknown'),
                        "minSelections": cust_group.get('minPermitted', 0),
                        "maxSelections": cust_group.get('maxPermitted', 1),
                        "options": []
                    }

                    for opt in cust_group.get('options', []):
                        option = {
                            "name": opt.get('title', ''),
                            "price": opt.get('price', 0) / 100,  # Convert from cents
                            "hasNestedOptions": bool(opt.get('childCustomizationList'))
                        }
                        group["options"].append(option)

                    customizations.append(group)

                all_customizations[product_title] = customizations

        except Exception as e:
            print(f"Error parsing {filepath}: {e}")

    return all_customizations


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    store_url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT_DIR

    asyncio.run(extract_options(store_url, output_dir))

    # Parse and display results
    print("\n\n📊 PARSING CAPTURED DATA...")
    customizations = parse_responses(output_dir)

    print(f"\n🎯 Found customizations for {len(customizations)} products:")
    for product, groups in list(customizations.items())[:5]:
        print(f"\n  {product}:")
        for g in groups[:3]:
            print(f"    - {g['title']} ({len(g['options'])} options)")
