---
name: Image Extraction
description: This skill should be used when the user asks to "extract images from Uber Eats", "download menu images", "get pictures from restaurant website", "scrape food photos", "map images to menu items", or needs to extract and correlate images from delivery platforms for catalog creation.
version: 1.0.0
---

# Image Extraction for Restaurant Catalogs

This skill provides techniques for extracting food images from restaurant websites and delivery platforms, with a focus on Uber Eats.

## Overview

Image extraction for catalogs involves:
1. **Finding image URLs** in website/platform HTML
2. **Downloading images** for inspection
3. **Correlating images** with menu items
4. **Updating catalog JSON** with image URLs

## Uber Eats Extraction

### Challenge

Uber Eats uses React with server-side rendering. The correlation between menu item names and image URLs is not directly available in static HTML—it's loaded dynamically by JavaScript.

### Solution: Download and Visual Identification

1. **Fetch the page** with browser-like headers to bypass rate limiting
2. **Extract all unique image URLs** from the HTML
3. **Download images** to a local folder
4. **Visually inspect** to identify which image belongs to which menu item
5. **Build the URL mapping** manually

### Step-by-Step Process

#### 1. Fetch Uber Eats Page

```bash
curl -s -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15" \
  "https://www.ubereats.com/fr-en/store/restaurant-name/store-id" \
  -o /tmp/ubereats.html
```

Key headers to include:
- User-Agent: Safari or Chrome user agent string
- Accept-Language: Appropriate locale

#### 2. Extract Unique Image URLs

```python
import re

with open('/tmp/ubereats.html', 'r') as f:
    html = f.read()

# Pattern for Uber Eats CDN images
pattern = r'tb-static\.uber\.com/prod/image-proc/processed_images/([a-f0-9]+)/([a-f0-9]+)\.(?:jpeg|png)'
matches = re.findall(pattern, html)

# Get unique images (first hash identifies the item)
seen = set()
images = []
for item_hash, size_hash in matches:
    if item_hash not in seen:
        seen.add(item_hash)
        url = f'https://tb-static.uber.com/prod/image-proc/processed_images/{item_hash}/{size_hash}.jpeg'
        images.append(url)
```

#### 3. Download for Inspection

```python
import urllib.request

for i, url in enumerate(images):
    filename = f'/tmp/ubereats_images/{i+1:02d}.jpeg'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        with open(filename, 'wb') as f:
            f.write(response.read())
```

#### 4. Visual Identification

Use the Read tool to view downloaded images and identify their contents:

```
Read /tmp/ubereats_images/01.jpeg
Read /tmp/ubereats_images/02.jpeg
...
```

Build a mapping as you identify each image:
- Image 39 = Perrier 33cl
- Image 40 = Vittel 50cl
- etc.

#### 5. Extract JSON-LD Menu Data

Uber Eats embeds menu data in JSON-LD format:

```python
import json
import re

# Find JSON-LD blocks
jsonld_pattern = r'<script[^>]*type="application/ld\+json"[^>]*>([^<]+)</script>'
matches = re.findall(jsonld_pattern, html)

for m in matches:
    m_clean = m.replace('\\u002F', '/')
    data = json.loads(m_clean)
    if data.get('@type') == 'Restaurant':
        # Extract menu sections and items
        menu = data.get('hasMenu', {})
        for section in menu.get('hasMenuSection', []):
            print(f"Section: {section['name']}")
            for item in section.get('hasMenuItem', []):
                print(f"  - {item['name']} | €{item['offers']['price']}")
```

## Website Image Extraction

### Webflow Sites

Many restaurant websites use Webflow. Images typically come from:
```
cdn.prod.website-files.com/[site-id]/[image-hash]_[filename].webp
```

Use WebFetch to get the page and extract image URLs:
```
WebFetch: https://www.restaurant-website.com/food
Prompt: Extract all image URLs from this page
```

### Direct HTML Parsing

For standard websites:

```python
import re

# Common patterns
patterns = [
    r'src="([^"]+\.(?:jpg|jpeg|png|webp))"',
    r'data-src="([^"]+\.(?:jpg|jpeg|png|webp))"',
    r'srcset="([^"]+\.(?:jpg|jpeg|png|webp))[^"]*"',
]

for pattern in patterns:
    matches = re.findall(pattern, html, re.IGNORECASE)
    for url in matches:
        print(url)
```

## Rate Limiting Bypass

### Browser-Like Headers

```bash
curl -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15" \
     -H "Accept: text/html,application/xhtml+xml" \
     -H "Accept-Language: en-US,en;q=0.9" \
     -H "Accept-Encoding: gzip, deflate, br" \
     "$URL"
```

### Delays Between Requests

When downloading multiple images, add delays:

```python
import time

for url in images:
    download(url)
    time.sleep(0.5)  # 500ms between requests
```

## Image URL Formats

### Uber Eats CDN

```
https://tb-static.uber.com/prod/image-proc/processed_images/{item_hash}/{size_hash}.jpeg
```

- `item_hash`: 32-char hex identifying the food item
- `size_hash`: 32-char hex for the image size variant
- Multiple sizes exist; any works for catalogs

### Webflow CDN

```
https://cdn.prod.website-files.com/{site_id}/{hash}_{filename}.webp
```

### Generic CDN

Look for patterns like:
- `images.squarespace-cdn.com/...`
- `res.cloudinary.com/...`
- `i.imgur.com/...`

## Correlation Strategies

### By Order of Appearance

Images often appear in the same order as menu items. Download all images, then match sequentially with the menu.

### By Image Filename

Some sites include item names in filenames:
```
margherita-pizza.jpg
carbonara-pasta.webp
```

### By Alt Text

Check `alt` attributes for item names:
```html
<img src="..." alt="Margherita Pizza">
```

### Visual Inspection

When automated correlation fails:
1. Download all images
2. Use Read tool to view each image
3. Manually identify and map to menu items

## Scripts

### Uber Eats Extraction Script

Use the script at `scripts/extract-ubereats.py`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/image-extraction/scripts/extract-ubereats.py \
  "https://www.ubereats.com/fr-en/store/restaurant-name/id" \
  /tmp/output_folder
```

This script:
1. Fetches the Uber Eats page
2. Extracts unique image URLs
3. Downloads all images
4. Extracts JSON-LD menu data
5. Outputs a mapping template

## Best Practices

1. **Always use browser-like headers** to avoid rate limiting
2. **Download to inspect** rather than guessing correlations
3. **Use JSON-LD data** from Uber Eats for accurate menu extraction
4. **Prefer HTTPS URLs** in the final catalog
5. **Check image availability** before adding to catalog
6. **Use high-quality variants** when multiple sizes exist
