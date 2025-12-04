# Catalog Schema Validation Rules

This document defines the complete validation rules for Chataigne catalog JSON files.

## Structure Validation

### Root Level

```json
{
  "catalog": { ... }
}
```

- Root must have a single `catalog` key
- `catalog` must be an object

### Catalog Object

Required fields:
- `name` (string): Restaurant name
- `categories` (array): At least one category
- `products` (array): At least one product

Optional fields:
- `settings` (object): Display preferences
- `optionLists` (array): Modifier groups
- `options` (array): Individual modifiers

## Field Validation Rules

### Category

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| name | string | Yes | Non-empty, unique |
| ref | string | Yes | UPPERCASE_SNAKE_CASE, unique |

### Option List

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| name | string | Yes | Non-empty, unique |
| ref | string | Yes | UPPERCASE_SNAKE_CASE, unique |
| minSelections | integer | Yes | >= 0 |
| maxSelections | integer | Yes | >= minSelections |

### Option

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| name | string | Yes | Non-empty |
| ref | string | Yes | UPPERCASE_SNAKE_CASE, unique |
| optionListName | string | Yes | Must match existing optionList.name |
| price | object | Yes | Has amount (number) and currency (string) |
| available | boolean | Yes | true/false |

### Product

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| name | string | Yes | Non-empty |
| description | string | No | - |
| categoryName | string | Yes | Must match existing category.name |
| imageUrl | string | No | Valid URL or empty string |
| available | boolean | Yes | true/false |
| sku | object | Yes | Has price object |
| sku.price | object | Yes | Has amount and currency |
| sku.optionListNames | array | No | Each must match existing optionList.name |

## Referential Integrity

### Foreign Key Checks

1. **product.categoryName** → Must exist in `categories[].name`
2. **product.sku.optionListNames[]** → Each must exist in `optionLists[].name`
3. **option.optionListName** → Must exist in `optionLists[].name`

### Orphan Detection

- Options without valid optionListName
- Products without valid categoryName
- OptionLists with no associated options (warning)
- Categories with no products (warning)

## Uniqueness Constraints

### Must Be Unique

- `category.ref` across all categories
- `category.name` across all categories
- `optionList.ref` across all option lists
- `optionList.name` across all option lists
- `option.ref` across all options
- `product.name` + `product.categoryName` combination

### Ref Naming Convention

All `ref` fields must follow UPPERCASE_SNAKE_CASE:
- Valid: `PIZZA_TOPPINGS`, `MAIN_COURSES`, `EXTRA_CHEESE`
- Invalid: `pizza-toppings`, `MainCourses`, `extra cheese`

## Price Validation

### Currency Codes

Must use ISO 4217 3-letter codes:
- Valid: `EUR`, `USD`, `CHF`, `GBP`
- Invalid: `€`, `euro`, `eur`

### Amount Values

- Must be non-negative numbers
- Decimals allowed (max 2 decimal places recommended)
- 0 is valid (for included options)

## Image URL Validation

### Accepted Formats

- HTTPS URLs (preferred)
- HTTP URLs (acceptable)
- Empty string (no image)

### Common CDN Patterns

- Webflow: `cdn.prod.website-files.com/...`
- Uber Eats: `tb-static.uber.com/prod/image-proc/...`
- Direct URLs: `restaurant-domain.com/images/...`

### Invalid

- Relative paths: `./images/pizza.jpg`
- Data URIs: `data:image/jpeg;base64,...`
- Missing protocol: `example.com/image.jpg`

## Business Rule Validation

### Menu Completeness

- Every category should have at least one product
- Every option list should have at least one option
- Products with optionListNames should have valid references

### Logical Constraints

- `minSelections` <= `maxSelections` for option lists
- If `minSelections` > 0, option list must have at least that many options
- Price amounts should be reasonable (warn if > 1000)

## Validation Output Format

```json
{
  "valid": false,
  "errors": [
    {
      "type": "INVALID_REFERENCE",
      "path": "products[5].categoryName",
      "message": "Category 'Appetizers' not found",
      "value": "Appetizers"
    }
  ],
  "warnings": [
    {
      "type": "EMPTY_CATEGORY",
      "path": "categories[2]",
      "message": "Category 'Sides' has no products"
    }
  ],
  "summary": {
    "categories": 5,
    "optionLists": 3,
    "options": 15,
    "products": 42,
    "productsWithImages": 38,
    "productsWithoutImages": 4
  }
}
```

## Error Types

| Type | Severity | Description |
|------|----------|-------------|
| MISSING_REQUIRED | Error | Required field is missing |
| INVALID_TYPE | Error | Field has wrong type |
| INVALID_REFERENCE | Error | Foreign key doesn't match |
| DUPLICATE_REF | Error | Ref is not unique |
| DUPLICATE_NAME | Error | Name is not unique (where required) |
| INVALID_REF_FORMAT | Error | Ref doesn't match UPPERCASE_SNAKE_CASE |
| INVALID_URL | Warning | Image URL format invalid |
| EMPTY_CATEGORY | Warning | Category has no products |
| EMPTY_OPTION_LIST | Warning | Option list has no options |
| MISSING_IMAGE | Warning | Product has no image URL |
| HIGH_PRICE | Warning | Price seems unusually high |
