---
name: create
description: Create a new restaurant catalog from menu data and images
argument-hint: <restaurant_name> [source_url]
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - WebFetch
  - AskUserQuestion
---

# Create Restaurant Catalog

Guide the user through creating a complete Chataigne catalog JSON file for a restaurant.

## Prerequisites

**IMPORTANT:** Before starting, load the catalog schema skill to understand the correct JSON structure:

```
Use Skill: catalog-builder:catalog-schema
```

This will help you avoid common mistakes like:
- Using `image` instead of `imageUrl`
- Using `minChoices` instead of `minSelections`
- Using refs instead of names for foreign keys
- Duplicate image URLs causing missing images after import

## Workflow

### Step 1: Gather Information

Ask the user for the following if not provided:
1. **Restaurant name**: Used for the catalog name
2. **Output path**: Where to save the catalog JSON (suggest `~/Downloads/{restaurant}-catalog.json`)
3. **Menu source**: One of:
   - Direct paste of menu data
   - Restaurant website URL
   - Uber Eats URL
   - Existing JSON/data file

### Step 2: Extract Menu Data

Based on the source:

**If pasted menu:**
- Parse the text to identify categories, items, prices, descriptions
- Ask clarifying questions about ambiguous items

**If website URL:**
- Use WebFetch to get the page content
- Extract menu sections, items, prices, and descriptions
- Look for image URLs on the page

**If Uber Eats URL:**
- Fetch the page with browser-like headers (use curl with Safari user agent)
- Extract JSON-LD structured data for menu items (categories, products, prices, descriptions)
- **Extract product-image mappings directly** (see "Uber Eats Image Extraction" section below)
- For OPTIONS data, search deeper in the page for customization groups

### Step 3: Define Categories

Based on extracted data:
1. Identify logical menu sections (Starters, Pizzas, Pasta, etc.)
2. Create category objects with names and refs
3. Confirm category list with user

### Step 4: Identify Options and Modifiers

Look for patterns indicating customization:
- "Choose your size"
- "Add toppings"
- "Select cooking preference"
- Kids menus with choices

Create option lists and options for each modifier group.

### Step 5: Create Products

For each menu item:
1. Assign to appropriate category (by name)
2. Extract price and description
3. Link to relevant option lists
4. Note which items need images

### Step 6: Extract and Assign Images

**From restaurant website:**
- Extract image URLs directly
- Match to products by filename or alt text

**From Uber Eats - Direct Extraction Method (PREFERRED):**

The Uber Eats HTML contains product-image mappings embedded in the page data. You can extract them directly **without downloading or visually inspecting images**:

```python
import re
import json

with open('/tmp/ubereats_page.html', 'r') as f:
    html = f.read()

# Pattern matches: imageUrl":"https://...","title":"Product Name"
pattern = r'imageUrl\\u0022:\\u0022(https://[^"\\]+)\\u0022,\\u0022title\\u0022:\\u0022([^"\\]+)\\u0022'
matches = re.findall(pattern, html)

# Build mapping: product_name -> image_url
product_images = {}
for url, title in matches:
    title = title.replace('\\u0026', '&')
    url = url.replace('\\u002F', '/')
    if title not in product_images:
        product_images[title] = url

print(f"Found {len(product_images)} product-image pairs!")
```

**Why this works:** Uber Eats embeds product data in the HTML as escaped JSON. Each product entry contains both `imageUrl` and `title` fields adjacent to each other, allowing direct extraction without image identification.

**Key benefits:**
- No need to download images to identify them
- No visual inspection required
- Works for 100+ products in seconds
- Also captures images for drinks, sides, and other options

**Don't forget to add images to OPTIONS too!** The extracted images include drinks, sauces, sides that can be matched to option choices.

**⚠️ After extraction, ensure unique URLs:**
Add query params (`?p=1`, `?p=2`) to any duplicate URLs to prevent Chataigne's import from only assigning images to one product.

### Step 7: Generate Catalog JSON

Create the catalog structure:
```json
{
  "catalog": {
    "name": "Restaurant Name",
    "settings": { "primaryCategories": [...] },
    "optionLists": [...],
    "options": [...],
    "categories": [...],
    "products": [...]
  }
}
```

Write to the specified output path.

### Step 8: Validate

Run validation to check:
- All foreign keys resolve correctly
- Required fields are present
- Image URLs are valid
- No duplicate refs

Report any issues and offer to fix them.

## Example Session

User: `/catalog-builder:create Pizzeria Mario`

Response:
1. Ask for menu source (website, Uber Eats, or paste)
2. Extract menu data
3. Show proposed categories, ask for confirmation
4. Identify options (toppings, sizes)
5. List products by category
6. Extract images, ask user to help identify any unclear ones
7. Generate and save catalog JSON
8. Validate and report summary

## ⚠️ Critical Schema Rules

**ALL foreign keys use NAMES, not refs:**

| Field | Must Reference |
|-------|----------------|
| `settings.primaryCategories` | Array of `category.name` values |
| `product.categoryName` | The `category.name` (not ref!) |
| `product.sku.optionListNames` | Array of `optionList.name` values |
| `option.optionListName` | The `optionList.name` (not ref!) |

**Correct structure for products:**
```json
{
  "name": "Menu Whopper",
  "ref": "MENU_WHOPPER",
  "categoryName": "Menus 🍔",        // ← Use category NAME
  "available": true,
  "sku": {
    "price": { "amount": 11.30, "currency": "EUR" },
    "optionListNames": ["Choix Boisson", "Choix Accompagnement"]  // ← Use option list NAMES
  }
}
```

**Correct structure for options:**
```json
{
  "name": "Coca-Cola",
  "ref": "DRINK_COCA",
  "optionListName": "Choix Boisson",  // ← Use option list NAME
  "price": { "amount": 0, "currency": "EUR" },
  "available": true
}
```

**Correct structure for option lists:**
```json
{
  "name": "Choix Boisson",
  "ref": "DRINK_CHOICE",
  "minSelections": 1,  // ← NOT minChoices!
  "maxSelections": 1   // ← NOT maxChoices!
}
```

## Important Notes

- Always confirm category structure with user before proceeding
- For Uber Eats, focus on extracting JSON-LD data for accurate pricing
- Exclude alcohol products unless user specifically requests them
- Use UPPERCASE_SNAKE_CASE for all ref fields
- Prices must be objects: `{ "amount": X, "currency": "EUR" }`
- Use category/option list NAMES (not refs) for all foreign key references

## Uber Eats Options Extraction

**IMPORTANT:** The JSON-LD data only contains products, NOT options/customizations!

Options data (sizes, toppings, sauces, drink choices for menus) are embedded deeper in the page's React state. To extract them:

1. **Search for customization patterns** in the HTML:
```python
# Look for customizationGroups or similar patterns
pattern = r'"customization[^"]*":\s*\[.*?\]'
# Or search for specific option-related fields
pattern = r'"title":"([^"]+)".*?"options":\[([^\]]+)\]'
```

2. **Look for option group structures** containing:
   - Group name (e.g., "Choix de la taille", "Sauces", "Boissons")
   - Min/max selections
   - Individual options with names and prices

3. **Match options to products** that reference them (menus typically have drink + side choices)

4. **Add images to options** using the same product_images mapping extracted earlier:
```python
# Options like "Coca-Cola" can use the same image as the product "Coca-Cola®"
option_to_product = {
    "Coca-Cola 33cl": "Coca-Cola®",
    "Frites": "Frites",
    "Nuggets x4": "Nuggets",
}
```

**If options data is not found in the page**, you may need to:
- Infer options from product descriptions (e.g., "Tailles et viandes au choix")
- Ask the user to provide the customization options manually
- Check if there's an API endpoint being called for product details
