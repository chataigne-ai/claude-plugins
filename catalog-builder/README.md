# Catalog Builder Plugin

Extract restaurant menus and images from websites and Uber Eats to create Chataigne catalog JSON files.

## Overview

This plugin automates the process of creating restaurant catalog JSON files for the Chataigne platform. It handles:

- **Menu extraction** from restaurant websites and Uber Eats
- **Image extraction** and correlation with menu items
- **Catalog JSON generation** following the Chataigne schema
- **Validation** for schema compliance and business rules

## Installation

Copy the plugin to your Claude plugins folder:

```bash
cp -r catalog-builder ~/.claude/plugins/
```

Or test locally:

```bash
cc --plugin-dir ~/.claude/plugins/catalog-builder
```

## Commands

### `/catalog-builder:create <restaurant_name> [source_url]`

Guided workflow to create a complete catalog from menu data and images.

**Example:**
```
/catalog-builder:create "Pizzeria Mario" https://www.ubereats.com/store/pizzeria-mario/id
```

### `/catalog-builder:extract-images <url> [output_folder]`

Extract and download images from Uber Eats or restaurant websites.

**Example:**
```
/catalog-builder:extract-images https://www.ubereats.com/store/restaurant/id /tmp/images
```

### `/catalog-builder:validate <catalog_path>`

Validate a catalog JSON file for schema compliance and business rules.

**Example:**
```
/catalog-builder:validate ~/Downloads/my-catalog.json
```

## Skills

### Catalog Schema

Triggers when asking about:
- "create a catalog"
- "build a menu JSON"
- "understand the catalog format"
- "add products to catalog"

Provides comprehensive knowledge of the Chataigne catalog JSON schema.

### Image Extraction

Triggers when asking about:
- "extract images from Uber Eats"
- "download menu images"
- "get pictures from restaurant website"

Provides techniques for extracting and correlating food images.

## Agents

### catalog-validator

Automatically validates catalogs after creation. Triggers on:
- After `/catalog-builder:create` completes
- "validate my catalog"
- "check catalog quality"

## Catalog Schema Overview

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

### Key Relationships

| Field | References | By |
|-------|------------|-----|
| `product.categoryName` | `category.name` | name |
| `product.sku.optionListNames` | `optionList.name` | name |
| `option.optionListName` | `optionList.name` | name |

### Naming Conventions

- **Refs**: UPPERCASE_SNAKE_CASE (e.g., `PIZZA_TOPPINGS`)
- **Names**: Display names, can include emojis

## Typical Workflow

1. **Gather sources**:
   - Restaurant website URL
   - Uber Eats store URL
   - Pasted menu text

2. **Run create command**:
   ```
   /catalog-builder:create "Restaurant Name"
   ```

3. **Follow guided workflow**:
   - Provide menu source
   - Confirm categories
   - Review extracted items
   - Help identify images

4. **Validate result**:
   ```
   /catalog-builder:validate ~/Downloads/restaurant-catalog.json
   ```

## Scripts

### validate-catalog.py

Standalone validation script:

```bash
python3 ~/.claude/plugins/catalog-builder/scripts/validate-catalog.py catalog.json
```

### extract-ubereats.py

Extract images from Uber Eats:

```bash
python3 ~/.claude/plugins/catalog-builder/skills/image-extraction/scripts/extract-ubereats.py \
  "https://www.ubereats.com/store/restaurant/id" \
  /tmp/output
```

## Tips

### Uber Eats Extraction

- Use browser-like headers to avoid rate limiting
- Download images to inspect visually
- JSON-LD data provides accurate menu structure
- Images appear roughly in menu order

### Image Correlation

- Download all images first
- Use `Read` tool to view each image
- Build mapping manually for accuracy
- Uber Eats CDN URLs are stable for catalogs

### Validation

- Run validation before importing to Chataigne
- Fix all errors (they will cause import failures)
- Warnings are advisory but should be addressed
- Check image coverage (aim for 90%+)

## Example Catalog

See `skills/catalog-schema/examples/sample-catalog.json` for a complete working example.

## License

MIT
