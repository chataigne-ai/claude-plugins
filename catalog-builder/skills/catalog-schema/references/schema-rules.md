# Catalog Schema Validation Rules

This document defines the complete validation rules for Chataigne catalog JSON files.

> **Note**: These rules are enforced by the `validate-catalog.py` script which mirrors the production validation in `catalog-import.service.ts`.

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
- `name` (string): Restaurant name, non-empty

Optional fields:
- `settings` (object): Display preferences
- `categories` (array): Menu sections
- `optionLists` (array): Modifier groups
- `options` (array): Individual modifiers
- `products` (array): Menu items
- `deals` (array): Combo meals/bundles
- `discounts` (array): Promotional discounts

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
| available | boolean | No | true/false (defaults to true) |
| sku | object | Yes | Has price object |
| sku.price | object | Yes | Has amount and currency |
| sku.optionListNames | array | No | Each must match existing optionList.name |
| sku.ref | string | No | UPPERCASE_SNAKE_CASE |

### Deal (Bundle/Combo)

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| name | string | Yes | Non-empty |
| ref | string | No | UPPERCASE_SNAKE_CASE |
| description | string | No | - |
| categoryName | string | Yes | Must match existing category.name |
| imageUrl | string | No | Valid URL or empty string |
| price | object | Yes | Has amount and currency |
| lines | array | Yes | At least 1 line |
| lines[].name | string | No | Optional line label |
| lines[].skus | array | Yes | At least 1 sku per line |
| lines[].skus[].skuName | string | Yes | Product name or "ProductName (options)" |
| lines[].skus[].price | object | No | Override price for this sku |

### Discount

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| name | string | Yes | Non-empty |
| level | string | Yes | "pushed", "public", or "hidden" |
| description | string | No | - |
| imageUrl | string | No | Valid URL or empty string |
| discountType | string | Yes | One of: percentage, fixed, free_product, bogo, free_shipping |
| discountData | object | Yes | Type-specific data (see below) |
| discountCondition | object | No | Conditions for discount application |

#### Discount Data by Type

| Type | Required Fields | Description |
|------|-----------------|-------------|
| percentage | `percentage` (number 1-100), optional `maxDiscountAmount` | Percentage off order |
| fixed | `amount` (number) | Fixed amount off |
| free_product | `productName` (string) | Free product with order |
| bogo | `productNames` (array of strings) | Buy one get one |
| free_shipping | (none) | Free delivery |

## Referential Integrity

### Foreign Key Checks

1. **product.categoryName** → Must exist in `categories[].name`
2. **product.sku.optionListNames[]** → Each must exist in `optionLists[].name`
3. **option.optionListName** → Must exist in `optionLists[].name`
4. **deal.categoryName** → Must exist in `categories[].name`
5. **deal.lines[].skus[].skuName** → Product name must exist in `products[].name`
6. **settings.primaryCategories[]** → Each must exist in `categories[].name`
7. **discount.discountData.productName** → Must exist in `products[].name` (for free_product)
8. **discount.discountData.productNames[]** → Each must exist in `products[].name` (for bogo)

### Fuzzy Match Suggestions

When a reference fails validation, the validator suggests similar names:

```
❌ Catégorie "Deserts" référencée dans le produit "Tiramisu" mais non définie
   (vouliez-vous dire "Desserts"?)
```

### Orphan Detection

- Options without valid optionListName → **Error**
- Products without valid categoryName → **Error**
- Deals without valid categoryName → **Error**
- OptionLists with no associated options → **Warning**
- Categories with no products → **Warning**

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

- Every category should have at least one product → **Warning**
- Every option list should have at least one option → **Warning**
- Products with optionListNames should have valid references → **Error**

### Option List Constraints

- `minSelections` must be >= 0 → **Error**
- `maxSelections` must be >= `minSelections` (or null for unlimited) → **Error**
- If `minSelections` > 0, option list should have at least that many options → **Warning**

### Deal Constraints

- Each deal must have at least 1 line → **Error**
- Each line must have at least 1 sku → **Error**
- Each sku must have a `skuName` → **Error**
- Product name in `skuName` must exist → **Error**

### Discount Constraints

- `level` must be one of: "pushed", "public", "hidden" → **Error**
- `discountType` must be valid → **Error**
- `discountData` must contain required fields for the type → **Error**
- `percentage` should be between 1 and 100 → **Warning**

### Price Validation

- Price amounts must be non-negative
- Prices must have `amount` and `currency` fields → **Error**
- Price amounts > 500 trigger a warning (unusually high)

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
| INVALID_REFERENCE | Error | Foreign key doesn't match (with fuzzy suggestions) |
| DUPLICATE_REF | Error | Ref is not unique |
| DUPLICATE_NAME | Error | Name is not unique (where required) |
| INVALID_REF_FORMAT | Warning | Ref doesn't match UPPERCASE_SNAKE_CASE (with suggestion) |
| INVALID_DISCOUNT_TYPE | Error | Discount type not recognized |
| INVALID_DISCOUNT_LEVEL | Error | Discount level not recognized |
| INVALID_DISCOUNT_DATA | Error | Missing required discountData fields for type |
| INVALID_SELECTIONS | Error | maxSelections < minSelections |
| INVALID_URL | Warning | Image URL format invalid |
| DUPLICATE_IMAGE_URL | Warning | Multiple products share same imageUrl (import bug!) |
| EMPTY_CATEGORY | Warning | Category has no products |
| EMPTY_OPTION_LIST | Warning | Option list has no options |
| MISSING_IMAGE | Warning | Product has no image URL |
| HIGH_PRICE | Warning | Price seems unusually high |
| INSUFFICIENT_OPTIONS | Warning | Option list has fewer options than minSelections |
