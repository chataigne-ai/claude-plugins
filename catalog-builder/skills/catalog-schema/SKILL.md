---
name: Catalog Schema
description: This skill should be used when the user asks to "create a catalog", "build a menu JSON", "understand the catalog format", "add products to catalog", "create option lists", "structure menu data", or needs guidance on Chataigne's catalog JSON schema for restaurant menus.
version: 1.0.0
---

# Chataigne Catalog Schema

This skill provides comprehensive knowledge of the Chataigne catalog JSON schema used for restaurant menu data.

## Schema Overview

A Chataigne catalog is a JSON structure containing:

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

## Core Entities

### Settings

Controls display order and preferences:

```json
"settings": {
  "primaryCategories": [
    "Starters",
    "Main Courses",
    "Desserts",
    "Drinks"
  ]
}
```

The `primaryCategories` array determines menu section ordering in the UI.

### Categories

Menu sections that group products:

```json
{
  "name": "Pizza Social Club 🍕",
  "ref": "PIZZAS"
}
```

- **name**: Display name (can include emojis)
- **ref**: Unique identifier (UPPERCASE_SNAKE_CASE)

### Option Lists

Groups of modifiers that can be attached to products:

```json
{
  "name": "Suppléments Pizza",
  "ref": "SUPPLEMENTS_PIZZA",
  "minSelections": 0,
  "maxSelections": 10
}
```

- **name**: Display name for the option group
- **ref**: Unique identifier
- **minSelections**: Minimum required selections (0 = optional)
- **maxSelections**: Maximum allowed selections

### Options

Individual modifiers within option lists:

```json
{
  "name": "Truffe fraîche",
  "ref": "TRUFFE_SUPPLEMENT",
  "optionListName": "Suppléments Pizza",
  "price": {
    "amount": 4.5,
    "currency": "EUR"
  },
  "available": true
}
```

- **optionListName**: Foreign key to the option list (by name, not ref)
- **price**: Can be 0 for free options

### Products

Menu items with pricing and options:

```json
{
  "name": "Truffle Mafia",
  "description": "Crème de truffe, mozzarella fior di latte, champignons...",
  "categoryName": "Pizza Social Club 🍕",
  "imageUrl": "https://cdn.example.com/image.webp",
  "available": true,
  "sku": {
    "price": {
      "amount": 22,
      "currency": "EUR"
    },
    "optionListNames": ["Suppléments Pizza", "Découpe Pizza"]
  }
}
```

**Critical relationships:**
- **categoryName**: References category by `name` (not ref)
- **optionListNames**: Array of option list names that apply to this product

## ⚠️ Common Mistakes (IMPORTANT)

These are the most frequent errors when creating catalogs:

### 1. Using refs instead of names for foreign keys

**WRONG** ❌
```json
{
  "categoryRef": "PIZZAS",
  "optionListRefs": ["TOPPINGS"]
}
```

**CORRECT** ✅
```json
{
  "categoryName": "Pizza Social Club 🍕",
  "sku": {
    "optionListNames": ["Suppléments Pizza"]
  }
}
```

### 2. Using refs in primaryCategories

**WRONG** ❌
```json
"settings": {
  "primaryCategories": ["PIZZAS", "DRINKS", "DESSERTS"]
}
```

**CORRECT** ✅
```json
"settings": {
  "primaryCategories": ["Pizza Social Club 🍕", "Boissons 🥤", "Desserts 🍦"]
}
```

### 3. Using simple numbers for prices

**WRONG** ❌
```json
"price": 15.50
```

**CORRECT** ✅
```json
"price": {
  "amount": 15.50,
  "currency": "EUR"
}
```

### 4. Using wrong field names for option lists

**WRONG** ❌
```json
{
  "minChoices": 1,
  "maxChoices": 5
}
```

**CORRECT** ✅
```json
{
  "minSelections": 1,
  "maxSelections": 5
}
```

### 5. Putting optionListNames at product root level

**WRONG** ❌
```json
{
  "name": "Margherita",
  "optionListNames": ["Toppings"],
  "price": { "amount": 12, "currency": "EUR" }
}
```

**CORRECT** ✅
```json
{
  "name": "Margherita",
  "sku": {
    "price": { "amount": 12, "currency": "EUR" },
    "optionListNames": ["Toppings"]
  }
}
```

### 6. Forgetting images on OPTIONS

Options can (and should!) have images too, not just products. Uber Eats extracts include images for drinks, sauces, sides, etc.

**WRONG** ❌
```json
{
  "name": "Coca-Cola",
  "ref": "DRINK_COCA",
  "optionListName": "Choix Boisson",
  "price": { "amount": 0, "currency": "EUR" },
  "available": true
}
```

**CORRECT** ✅
```json
{
  "name": "Coca-Cola",
  "ref": "DRINK_COCA",
  "optionListName": "Choix Boisson",
  "price": { "amount": 0, "currency": "EUR" },
  "available": true,
  "imageUrl": "https://tb-static.uber.com/prod/image-proc/processed_images/..."
}
```

### 7. Using the SAME image URL for multiple products (CRITICAL!)

When multiple products share the exact same `imageUrl`, Chataigne's import process downloads the image ONCE but only assigns the S3 URL to ONE product. All other products sharing that URL will have NO image after import!

**WRONG** ❌ (All 3 formulas share same URL - only 1 will get the image!)
```json
[
  {
    "name": "4 ingrédients + Boisson",
    "imageUrl": "https://example.com/formula.jpg"
  },
  {
    "name": "6 ingrédients + Boisson",
    "imageUrl": "https://example.com/formula.jpg"
  },
  {
    "name": "8 ingrédients + Boisson",
    "imageUrl": "https://example.com/formula.jpg"
  }
]
```

**CORRECT** ✅ (Add unique query params to make each URL unique)
```json
[
  {
    "name": "4 ingrédients + Boisson",
    "imageUrl": "https://example.com/formula.jpg?p=1"
  },
  {
    "name": "6 ingrédients + Boisson",
    "imageUrl": "https://example.com/formula.jpg?p=2"
  },
  {
    "name": "8 ingrédients + Boisson",
    "imageUrl": "https://example.com/formula.jpg?p=3"
  }
]
```

**Why this happens:** Chataigne's import deduplicates image downloads by URL. When it encounters a duplicate URL, it should reuse the already-uploaded S3 image for all products, but there's a bug where only the first (or last) product gets the imageUrl assigned.

**The fix:** Add unique query parameters (`?p=1`, `?p=2`, `?o=1` for options) to force each URL to be treated as unique. The CDN ignores unknown query params but Chataigne sees them as different URLs.

---

## Key Schema Rules

### Foreign Keys by Name

Unlike typical databases, Chataigne uses **name-based foreign keys**:

| Field | References | By |
|-------|------------|-----|
| `settings.primaryCategories` | `category.name` | name |
| `product.categoryName` | `category.name` | name |
| `product.sku.optionListNames` | `optionList.name` | name |
| `option.optionListName` | `optionList.name` | name |

This makes the JSON human-readable but requires exact string matching (including emojis!).

### Required Fields

**Categories**: `name`, `ref`
**Option Lists**: `name`, `ref`, `minSelections`, `maxSelections`
**Options**: `name`, `ref`, `optionListName`, `price`, `available`
**Products**: `name`, `categoryName`, `available`, `sku` (with `price`)

### Optional Fields

**Products**: `description`, `imageUrl`, `sku.optionListNames`

### Currency Format

Always use ISO 4217 currency codes:

```json
"price": {
  "amount": 15.50,
  "currency": "EUR"
}
```

## Common Patterns

### Pizza with Toppings

```json
// Option list for toppings
{
  "name": "Pizza Toppings",
  "ref": "PIZZA_TOPPINGS",
  "minSelections": 0,
  "maxSelections": 5
}

// Individual topping options
{
  "name": "Extra Cheese",
  "ref": "EXTRA_CHEESE",
  "optionListName": "Pizza Toppings",
  "price": { "amount": 2.5, "currency": "EUR" },
  "available": true
}

// Pizza product with toppings
{
  "name": "Margherita",
  "categoryName": "Pizzas",
  "sku": {
    "price": { "amount": 12, "currency": "EUR" },
    "optionListNames": ["Pizza Toppings"]
  }
}
```

### Kids Menu with Choices

For combo meals with required selections:

```json
// Required main course choice
{
  "name": "Kids Main Choice",
  "ref": "KIDS_MAIN",
  "minSelections": 1,
  "maxSelections": 1
}

// Options for the choice
{
  "name": "Mini Pizza",
  "ref": "KIDS_PIZZA",
  "optionListName": "Kids Main Choice",
  "price": { "amount": 0, "currency": "EUR" },
  "available": true
}

// Kids menu product
{
  "name": "Kids Menu",
  "categoryName": "Menus",
  "sku": {
    "price": { "amount": 12, "currency": "EUR" },
    "optionListNames": ["Kids Main Choice", "Kids Dessert Choice", "Kids Drink Choice"]
  }
}
```

## Catalog Creation Workflow

1. **Gather source data**: Restaurant website, Uber Eats, provided menu
2. **Define categories**: Create category objects for each menu section
3. **Create option lists**: Identify modifier groups (toppings, sizes, etc.)
4. **Add options**: Define individual modifiers for each list
5. **Add products**: Create product entries with category/option references
6. **Add images**: Extract and assign image URLs
7. **Validate**: Run schema validation to check integrity

## Additional Resources

### Reference Files

For complete examples and validation rules:
- **`references/schema-rules.md`** - Detailed validation rules and constraints
- **`examples/sample-catalog.json`** - Complete working catalog example

### Validation

Use the `/catalog-builder:validate` command to check catalog integrity:

**Errors (blocks import):**
- Missing required fields (name, categoryName, sku, etc.)
- Invalid foreign key references (with fuzzy "did you mean?" suggestions)
- Duplicate refs or names
- Invalid discount type/level
- Deal structure issues (missing lines, skus, skuName)
- Option list constraint violations (maxSelections < minSelections)

**Warnings (import will work but may have issues):**
- Missing images on products/options
- Duplicate image URLs (import bug - only 1 product gets the image!)
- Empty categories or option lists
- Invalid ref format (suggests UPPERCASE_SNAKE_CASE)
- Insufficient options for minSelections

Run validation directly:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate-catalog.py /path/to/catalog.json
```
