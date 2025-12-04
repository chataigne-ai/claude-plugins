---
name: extract-images
description: Extract and download images from Uber Eats or restaurant websites
argument-hint: <url> [output_folder]
allowed-tools:
  - Read
  - Write
  - Bash
  - WebFetch
---

# Extract Images

Download and organize food images from restaurant websites or Uber Eats for catalog creation.

## Usage

```
/catalog-builder:extract-images https://www.ubereats.com/store/restaurant/id
/catalog-builder:extract-images https://www.restaurant.com/menu /tmp/images
```

## Workflow

### Step 1: Identify Source Type

Detect the source based on URL:
- `ubereats.com` → Uber Eats extraction flow
- Other → Generic website extraction

### Step 2: Set Output Location

Use the provided output folder or default to `/tmp/{restaurant}_images`

### Step 3: Fetch and Extract

**For Uber Eats:**

1. Fetch the page with browser headers:
```bash
curl -s -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15" \
  "$URL" -o /tmp/ubereats.html
```

2. Extract unique image URLs using Python:
```python
import re
pattern = r'tb-static\.uber\.com/prod/image-proc/processed_images/([a-f0-9]+)/([a-f0-9]+)\.(?:jpeg|png)'
# Extract and dedupe by first hash
```

3. Download all images to output folder with numbered filenames

4. Extract JSON-LD menu data for reference

**For generic websites:**

1. Use WebFetch to get page content
2. Extract image URLs using patterns:
   - `src="..."` attributes
   - `data-src="..."` for lazy-loaded images
   - `srcset` attributes
3. Filter for food-related images (exclude logos, icons, UI elements)
4. Download to output folder

### Step 4: Report Results

Output:
- Number of unique images found
- Number successfully downloaded
- Location of downloaded images
- JSON-LD menu data summary (for Uber Eats)

### Step 5: Provide Next Steps

Explain how to use the images:
1. View images to identify menu items
2. Create mapping between image filenames and product names
3. Use the Uber Eats CDN URLs directly in catalog (no need to host)

## Image URL Formats

### Uber Eats

Full URL format:
```
https://tb-static.uber.com/prod/image-proc/processed_images/{item_hash}/{size_hash}.jpeg
```

These URLs are stable and can be used directly in the catalog.

### Webflow

```
https://cdn.prod.website-files.com/{site_id}/{image_id}_{filename}.webp
```

### Tips

- Uber Eats images appear in roughly menu order
- Use the Read tool to view downloaded images for identification
- Drinks and desserts typically appear after main items
- Wine/alcohol images can be skipped (usually last)

## Example Output

```
=== Image Extraction Summary ===
Source: Uber Eats (Restaurant Name)
Images found: 67
Images downloaded: 66 (1 failed)
Output folder: /tmp/restaurant_images/

Menu items found (from JSON-LD):
- PIZZA SOCIAL CLUB: 15 items
- PASTA: 7 items
- DESSERTS: 7 items
- DRINKS: 8 items

Next steps:
1. View images: ls /tmp/restaurant_images/
2. Use Read tool to inspect each image
3. Map images to menu items
4. Update catalog with imageUrl fields
```
