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

> **Note**: This validation mirrors the production logic from `catalog-import.service.ts` to catch errors before import.

## Usage

```
/catalog-builder:validate /path/to/catalog.json
```

## Validation Process

### Step 1: Load and Parse

Read the catalog JSON file and verify it's valid JSON.

### Step 2: Root Structure

- Root has `catalog` object
- `catalog.name` exists and is non-empty string

### Step 3: Entity Structure Validation

For each **category**:
- Has `name` (string, required)
- Has `ref` (string, recommended UPPERCASE_SNAKE_CASE)

For each **optionList**:
- Has `name` (string, required)
- Has `ref` (string, recommended)
- `minSelections` >= 0 if present
- `maxSelections` >= `minSelections` if both present

For each **option**:
- Has `name` (string, required)
- Has `optionListName` (string, required)
- Has `price` object with `amount` (number) and `currency` (string)

For each **product**:
- Has `name` (string, required)
- Has `categoryName` (string, required)
- Has `sku` object with `price`

For each **deal**:
- Has `name` (string, required)
- Has `categoryName` (string, required)
- Has `price` object with `amount` and `currency`
- Has `lines` array with at least 1 line
- Each line has `skus` array with at least 1 sku
- Each sku has `skuName` (string, required)

For each **discount**:
- Has `name` (string, required)
- Has `level` (one of: "pushed", "public", "hidden")
- Has `discountType` (one of: percentage, fixed, free_product, bogo, free_shipping)
- Has required `discountData` fields for the type

### Step 4: Referential Integrity (with Fuzzy Matching)

Check all foreign key references:
- Every `product.categoryName` → existing `category.name`
- Every `product.sku.optionListNames[]` → existing `optionList.name`
- Every `option.optionListName` → existing `optionList.name`
- Every `deal.categoryName` → existing `category.name`
- Every `deal.lines[].skus[].skuName` → existing `product.name`
- Every `settings.primaryCategories[]` → existing `category.name`
- Every `discount.discountData.productName` → existing `product.name`
- Every `discount.discountData.productNames[]` → existing `product.name`

**Fuzzy matching**: When a reference fails, suggests similar names ("Did you mean...?")

### Step 5: Uniqueness Checks

- All `category.ref` values are unique
- All `category.name` values are unique
- All `optionList.ref` values are unique
- All `optionList.name` values are unique
- All `option.ref` values are unique
- All `product.ref` values are unique (if present)

### Step 6: Naming Convention Checks (Warnings)

- All `ref` values should follow UPPERCASE_SNAKE_CASE pattern
- Pattern: `^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$`
- Suggests corrected format for invalid refs

### Step 7: Business Rules

Check logical constraints:
- Categories should have at least one product (warning)
- Option lists should have at least one option (warning)
- If `minSelections` > 0, verify enough options exist (warning)
- Price amounts should be non-negative
- Percentage discounts should be between 1-100 (warning)

### Step 8: Image Checks

- Products without `imageUrl` flagged as warning
- Options without `imageUrl` counted
- **Duplicate image URLs detected** - warns about import bug where only 1 product gets the image

## Output Format

```
=======================================================
  CHATAIGNE CATALOG VALIDATION REPORT
=======================================================

📦 Catalog: Restaurant Name

📊 Contents:
   • Categories: 7
   • Products: 45
   • Option Lists: 4
   • Options: 18
   • Deals: 3
   • Discounts: 2

✅ No errors found!

⚠️  WARNINGS (3):
   • 2 produit(s) sans image: Bread, Grana Padano
   • Catégorie "Sides" n'a aucun produit
   • Ref de catégorie "main-courses" ne suit pas UPPERCASE_SNAKE_CASE (suggestion: MAIN_COURSES)

=======================================================
  ✅ VALID (with warnings)
=======================================================
```

If errors are found:

```
=======================================================
  CHATAIGNE CATALOG VALIDATION REPORT
=======================================================

📦 Catalog: Restaurant Name

📊 Contents:
   • Categories: 5
   • Products: 20
   • ...

❌ ERRORS (3):
   • Catégorie "Desert" référencée dans le produit "Tiramisu" mais non définie (vouliez-vous dire "Desserts"?)
   • Liste d'options "Size": maxSelections (1) doit être >= minSelections (2)
   • Discount "Summer Sale": "level" est requis

=======================================================
  ❌ INVALID - Fix errors before importing
=======================================================
```

## Using the Validation Script

Run the validation script directly:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate-catalog.py /path/to/catalog.json
```

Exit codes:
- `0` - Valid catalog
- `1` - Invalid (has errors)
- `2` - File not found or JSON parse error

## Validation Features

| Feature | Description |
|---------|-------------|
| **Fuzzy Matching** | Suggests corrections for typos in references |
| **Ref Suggestions** | Converts invalid refs to UPPERCASE_SNAKE_CASE |
| **Duplicate Image Detection** | Warns about import bug with shared URLs |
| **Discount Type Validation** | Validates discountData per discount type |
| **Deal Structure** | Validates lines/skus structure |
| **Selection Constraints** | Checks min/max selections logic |
