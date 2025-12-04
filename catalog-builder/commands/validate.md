---
name: validate
description: Validate a catalog JSON file for schema compliance and business rules
argument-hint: <catalog_path>
allowed-tools:
  - Read
  - Bash
---

# Validate Catalog

Validate a Chataigne catalog JSON file for schema compliance, referential integrity, and business rules.

## Usage

```
/catalog-builder:validate /path/to/catalog.json
```

## Validation Process

### Step 1: Load and Parse

Read the catalog JSON file and verify it's valid JSON.

### Step 2: Schema Validation

Check required structure:
- Root has `catalog` object
- `catalog.name` exists and is non-empty string
- `catalog.categories` is non-empty array
- `catalog.products` is non-empty array

For each **category**:
- Has `name` (string, non-empty)
- Has `ref` (string, UPPERCASE_SNAKE_CASE)

For each **optionList**:
- Has `name`, `ref`
- Has `minSelections` (integer >= 0)
- Has `maxSelections` (integer >= minSelections)

For each **option**:
- Has `name`, `ref`, `optionListName`
- Has `price` object with `amount` (number) and `currency` (string)
- Has `available` (boolean)

For each **product**:
- Has `name`, `categoryName`, `available`
- Has `sku.price` with `amount` and `currency`

### Step 3: Referential Integrity

Check all foreign key references:
- Every `product.categoryName` must match an existing `category.name`
- Every `product.sku.optionListNames[]` must match existing `optionList.name`
- Every `option.optionListName` must match existing `optionList.name`

### Step 4: Uniqueness Checks

- All `category.ref` values are unique
- All `category.name` values are unique
- All `optionList.ref` values are unique
- All `optionList.name` values are unique
- All `option.ref` values are unique

### Step 5: Naming Convention Checks

- All `ref` values follow UPPERCASE_SNAKE_CASE pattern
- Pattern: `^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$`

### Step 6: Business Rules

Check logical constraints:
- Categories should have at least one product (warning if empty)
- Option lists should have at least one option (warning if empty)
- If optionList.minSelections > 0, verify enough options exist
- Price amounts should be non-negative
- Price amounts > 500 trigger a warning (unusually high)

### Step 7: Image Checks

For each product:
- If `imageUrl` is empty string, flag as missing image
- If `imageUrl` is present, verify URL format (starts with http:// or https://)

## Output Format

Display a structured validation report:

```
=== Catalog Validation Report ===

Catalog: Restaurant Name

✓ Schema Validation: PASSED
✓ Referential Integrity: PASSED
✓ Uniqueness Checks: PASSED
✓ Naming Conventions: PASSED

⚠ Warnings:
  - Product "Bread" has no image URL
  - Product "Grana Padano" has no image URL
  - Category "Sides" has no products

Summary:
  Categories: 7
  Option Lists: 4
  Options: 18
  Products: 45
  Products with images: 43 (96%)
  Products without images: 2

Overall: VALID (with 3 warnings)
```

If errors are found:

```
=== Catalog Validation Report ===

✗ Referential Integrity: FAILED
  - Product "Tiramisu" references category "Desert" which does not exist
    (Did you mean "Desserts"?)
  - Option "Extra Cheese" references optionList "Topings" which does not exist
    (Did you mean "Toppings"?)

✗ Uniqueness Checks: FAILED
  - Duplicate category ref: "MAIN"

Summary:
  Errors: 3
  Warnings: 0

Overall: INVALID
```

## Auto-Fix Suggestions

For common errors, suggest fixes:

- Typos in foreign keys: Suggest similar names using fuzzy matching
- Missing refs: Generate suggested ref from name
- Invalid ref format: Suggest converted UPPERCASE_SNAKE_CASE version

## Using the Validation Script

Run the validation script directly:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate-catalog.py /path/to/catalog.json
```

Or use the Read tool to load the file and perform validation manually.
