#!/usr/bin/env python3
"""
Uber Eats Image Extractor

Extracts menu images and item data from Uber Eats store pages.

Usage:
    python3 extract-ubereats.py <ubereats_url> <output_folder>

Example:
    python3 extract-ubereats.py "https://www.ubereats.com/fr-en/store/restaurant/id" /tmp/images
"""

import sys
import os
import re
import json
import urllib.request
import time
from pathlib import Path


def fetch_page(url: str) -> str:
    """Fetch Uber Eats page with browser-like headers."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode('utf-8')


def extract_image_urls(html: str) -> list[tuple[str, str]]:
    """Extract unique Uber Eats CDN image URLs."""
    pattern = r'tb-static\.uber\.com/prod/image-proc/processed_images/([a-f0-9]+)/([a-f0-9]+)\.(?:jpeg|png)'
    matches = re.findall(pattern, html)

    seen = set()
    images = []
    for item_hash, size_hash in matches:
        if item_hash not in seen:
            seen.add(item_hash)
            url = f'https://tb-static.uber.com/prod/image-proc/processed_images/{item_hash}/{size_hash}.jpeg'
            images.append((item_hash[:12], url))

    return images


def extract_menu_data(html: str) -> list[dict]:
    """Extract menu items from JSON-LD structured data."""
    jsonld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>([^<]+)</script>'
    matches = re.findall(jsonld_pattern, html)

    menu_items = []
    for m in matches:
        try:
            m_clean = m.replace('\\u002F', '/')
            data = json.loads(m_clean)

            if data.get('@type') == 'Restaurant':
                menu = data.get('hasMenu', {})
                for section in menu.get('hasMenuSection', []):
                    section_name = section.get('name', 'Unknown')
                    for item in section.get('hasMenuItem', []):
                        menu_items.append({
                            'section': section_name,
                            'name': item.get('name', ''),
                            'description': item.get('description', ''),
                            'price': item.get('offers', {}).get('price', ''),
                            'currency': item.get('offers', {}).get('priceCurrency', 'EUR'),
                        })
        except json.JSONDecodeError:
            continue

    return menu_items


def download_images(images: list[tuple[str, str]], output_folder: Path) -> list[str]:
    """Download images to output folder."""
    output_folder.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for i, (hash_prefix, url) in enumerate(images):
        filename = f'{i+1:02d}_{hash_prefix}.jpeg'
        filepath = output_folder / filename

        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                with open(filepath, 'wb') as f:
                    f.write(response.read())
            downloaded.append(filename)
            print(f'✓ Downloaded {filename}')
            time.sleep(0.3)  # Rate limiting
        except Exception as e:
            print(f'✗ Failed {filename}: {e}')

    return downloaded


def create_mapping_template(images: list[tuple[str, str]], menu_items: list[dict], output_folder: Path):
    """Create a mapping template file."""
    template = {
        'instructions': 'Fill in the image_index for each menu item after visually inspecting the downloaded images',
        'images': [{'index': i+1, 'hash': h, 'url': u, 'identified_as': ''} for i, (h, u) in enumerate(images)],
        'menu_items': menu_items,
    }

    with open(output_folder / 'mapping-template.json', 'w') as f:
        json.dump(template, f, indent=2, ensure_ascii=False)

    print(f'\n✓ Created mapping-template.json')


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    url = sys.argv[1]
    output_folder = Path(sys.argv[2])

    print(f'Fetching: {url}')
    html = fetch_page(url)
    print(f'✓ Fetched {len(html):,} bytes')

    # Save HTML for debugging
    with open(output_folder / 'page.html', 'w') as f:
        f.write(html)

    # Extract images
    images = extract_image_urls(html)
    print(f'\n✓ Found {len(images)} unique images')

    # Extract menu data
    menu_items = extract_menu_data(html)
    print(f'✓ Found {len(menu_items)} menu items')

    # Download images
    print(f'\nDownloading images to {output_folder}...')
    downloaded = download_images(images, output_folder)

    # Create mapping template
    create_mapping_template(images, menu_items, output_folder)

    print(f'\n=== Summary ===')
    print(f'Images downloaded: {len(downloaded)}')
    print(f'Menu items found: {len(menu_items)}')
    print(f'Output folder: {output_folder}')
    print(f'\nNext steps:')
    print(f'1. View images in {output_folder}')
    print(f'2. Edit mapping-template.json to correlate images with menu items')
    print(f'3. Use the mapping to update your catalog JSON')


if __name__ == '__main__':
    main()
