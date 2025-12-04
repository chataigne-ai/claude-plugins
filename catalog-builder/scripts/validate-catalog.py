#!/usr/bin/env python3
"""
Chataigne Catalog Validator

Validates catalog JSON files for schema compliance, referential integrity,
and business rules.

Usage:
    python3 validate-catalog.py <catalog_path>

Exit codes:
    0 - Valid (may have warnings)
    1 - Invalid (has errors)
    2 - File not found or parse error
"""

import sys
import json
import re
from pathlib import Path
from difflib import get_close_matches


def load_catalog(path: str) -> dict:
    """Load and parse catalog JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_ref_format(ref: str) -> bool:
    """Check if ref follows UPPERCASE_SNAKE_CASE."""
    return bool(re.match(r'^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$', ref))


def validate_url(url: str) -> bool:
    """Check if URL is valid format."""
    if not url:
        return True  # Empty is allowed
    return url.startswith('http://') or url.startswith('https://')


def suggest_ref(name: str) -> str:
    """Generate suggested ref from name."""
    # Remove emojis and special chars
    cleaned = re.sub(r'[^\w\s]', '', name)
    # Convert to UPPERCASE_SNAKE_CASE
    return re.sub(r'\s+', '_', cleaned.strip().upper())


def validate_catalog(catalog: dict) -> tuple[list[dict], list[dict], dict]:
    """
    Validate catalog and return (errors, warnings, summary).
    """
    errors = []
    warnings = []

    # Check root structure
    if 'catalog' not in catalog:
        errors.append({
            'type': 'MISSING_ROOT',
            'message': 'Root object must have "catalog" key'
        })
        return errors, warnings, {}

    cat = catalog['catalog']

    # Check required fields
    if not cat.get('name'):
        errors.append({
            'type': 'MISSING_REQUIRED',
            'path': 'catalog.name',
            'message': 'Catalog name is required'
        })

    categories = cat.get('categories', [])
    if not categories:
        errors.append({
            'type': 'MISSING_REQUIRED',
            'path': 'catalog.categories',
            'message': 'At least one category is required'
        })

    products = cat.get('products', [])
    if not products:
        errors.append({
            'type': 'MISSING_REQUIRED',
            'path': 'catalog.products',
            'message': 'At least one product is required'
        })

    option_lists = cat.get('optionLists', [])
    options = cat.get('options', [])

    # Build lookup maps
    category_names = set()
    category_refs = set()
    option_list_names = set()
    option_list_refs = set()
    option_refs = set()

    # Validate categories
    for i, c in enumerate(categories):
        path = f'categories[{i}]'

        if not c.get('name'):
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.name',
                'message': 'Category name is required'
            })
        else:
            if c['name'] in category_names:
                errors.append({
                    'type': 'DUPLICATE_NAME',
                    'path': f'{path}.name',
                    'message': f'Duplicate category name: "{c["name"]}"'
                })
            category_names.add(c['name'])

        if not c.get('ref'):
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.ref',
                'message': f'Category "{c.get("name", i)}" missing ref'
            })
        else:
            if c['ref'] in category_refs:
                errors.append({
                    'type': 'DUPLICATE_REF',
                    'path': f'{path}.ref',
                    'message': f'Duplicate category ref: "{c["ref"]}"'
                })
            category_refs.add(c['ref'])

            if not validate_ref_format(c['ref']):
                errors.append({
                    'type': 'INVALID_REF_FORMAT',
                    'path': f'{path}.ref',
                    'message': f'Ref "{c["ref"]}" should be UPPERCASE_SNAKE_CASE',
                    'suggestion': suggest_ref(c.get('name', c['ref']))
                })

    # Validate option lists
    for i, ol in enumerate(option_lists):
        path = f'optionLists[{i}]'

        if not ol.get('name'):
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.name',
                'message': 'Option list name is required'
            })
        else:
            if ol['name'] in option_list_names:
                errors.append({
                    'type': 'DUPLICATE_NAME',
                    'path': f'{path}.name',
                    'message': f'Duplicate option list name: "{ol["name"]}"'
                })
            option_list_names.add(ol['name'])

        if not ol.get('ref'):
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.ref',
                'message': f'Option list "{ol.get("name", i)}" missing ref'
            })
        else:
            if ol['ref'] in option_list_refs:
                errors.append({
                    'type': 'DUPLICATE_REF',
                    'path': f'{path}.ref',
                    'message': f'Duplicate option list ref: "{ol["ref"]}"'
                })
            option_list_refs.add(ol['ref'])

            if not validate_ref_format(ol['ref']):
                errors.append({
                    'type': 'INVALID_REF_FORMAT',
                    'path': f'{path}.ref',
                    'message': f'Ref "{ol["ref"]}" should be UPPERCASE_SNAKE_CASE',
                    'suggestion': suggest_ref(ol.get('name', ol['ref']))
                })

        if 'minSelections' not in ol:
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.minSelections',
                'message': f'Option list "{ol.get("name", i)}" missing minSelections'
            })
        elif ol['minSelections'] < 0:
            errors.append({
                'type': 'INVALID_VALUE',
                'path': f'{path}.minSelections',
                'message': 'minSelections must be >= 0'
            })

        if 'maxSelections' not in ol:
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.maxSelections',
                'message': f'Option list "{ol.get("name", i)}" missing maxSelections'
            })
        elif 'minSelections' in ol and ol['maxSelections'] < ol['minSelections']:
            errors.append({
                'type': 'INVALID_VALUE',
                'path': f'{path}.maxSelections',
                'message': 'maxSelections must be >= minSelections'
            })

    # Validate options
    for i, o in enumerate(options):
        path = f'options[{i}]'

        if not o.get('name'):
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.name',
                'message': 'Option name is required'
            })

        if not o.get('ref'):
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.ref',
                'message': f'Option "{o.get("name", i)}" missing ref'
            })
        else:
            if o['ref'] in option_refs:
                errors.append({
                    'type': 'DUPLICATE_REF',
                    'path': f'{path}.ref',
                    'message': f'Duplicate option ref: "{o["ref"]}"'
                })
            option_refs.add(o['ref'])

            if not validate_ref_format(o['ref']):
                errors.append({
                    'type': 'INVALID_REF_FORMAT',
                    'path': f'{path}.ref',
                    'message': f'Ref "{o["ref"]}" should be UPPERCASE_SNAKE_CASE',
                    'suggestion': suggest_ref(o.get('name', o['ref']))
                })

        if not o.get('optionListName'):
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.optionListName',
                'message': f'Option "{o.get("name", i)}" missing optionListName'
            })
        elif o['optionListName'] not in option_list_names:
            suggestion = get_close_matches(o['optionListName'], list(option_list_names), n=1)
            errors.append({
                'type': 'INVALID_REFERENCE',
                'path': f'{path}.optionListName',
                'message': f'Option list "{o["optionListName"]}" not found',
                'suggestion': suggestion[0] if suggestion else None
            })

        if 'price' not in o:
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.price',
                'message': f'Option "{o.get("name", i)}" missing price'
            })
        else:
            if 'amount' not in o['price']:
                errors.append({
                    'type': 'MISSING_REQUIRED',
                    'path': f'{path}.price.amount',
                    'message': 'Price amount is required'
                })
            if 'currency' not in o['price']:
                errors.append({
                    'type': 'MISSING_REQUIRED',
                    'path': f'{path}.price.currency',
                    'message': 'Price currency is required'
                })

        if 'available' not in o:
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.available',
                'message': f'Option "{o.get("name", i)}" missing available field'
            })

    # Validate products
    products_per_category = {name: 0 for name in category_names}
    products_with_images = 0
    products_without_images = []

    for i, p in enumerate(products):
        path = f'products[{i}]'

        if not p.get('name'):
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.name',
                'message': 'Product name is required'
            })

        if not p.get('categoryName'):
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.categoryName',
                'message': f'Product "{p.get("name", i)}" missing categoryName'
            })
        elif p['categoryName'] not in category_names:
            suggestion = get_close_matches(p['categoryName'], list(category_names), n=1)
            errors.append({
                'type': 'INVALID_REFERENCE',
                'path': f'{path}.categoryName',
                'message': f'Category "{p["categoryName"]}" not found',
                'suggestion': suggestion[0] if suggestion else None
            })
        else:
            products_per_category[p['categoryName']] += 1

        if 'available' not in p:
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.available',
                'message': f'Product "{p.get("name", i)}" missing available field'
            })

        if 'sku' not in p:
            errors.append({
                'type': 'MISSING_REQUIRED',
                'path': f'{path}.sku',
                'message': f'Product "{p.get("name", i)}" missing sku'
            })
        else:
            if 'price' not in p['sku']:
                errors.append({
                    'type': 'MISSING_REQUIRED',
                    'path': f'{path}.sku.price',
                    'message': f'Product "{p.get("name", i)}" missing sku.price'
                })
            else:
                price = p['sku']['price']
                if 'amount' not in price:
                    errors.append({
                        'type': 'MISSING_REQUIRED',
                        'path': f'{path}.sku.price.amount',
                        'message': 'Price amount is required'
                    })
                elif price['amount'] < 0:
                    errors.append({
                        'type': 'INVALID_VALUE',
                        'path': f'{path}.sku.price.amount',
                        'message': 'Price amount must be non-negative'
                    })
                elif price['amount'] > 500:
                    warnings.append({
                        'type': 'HIGH_PRICE',
                        'path': f'{path}.sku.price.amount',
                        'message': f'Product "{p.get("name", i)}" has unusually high price: {price["amount"]}'
                    })

                if 'currency' not in price:
                    errors.append({
                        'type': 'MISSING_REQUIRED',
                        'path': f'{path}.sku.price.currency',
                        'message': 'Price currency is required'
                    })

            # Check optionListNames references
            for j, oln in enumerate(p['sku'].get('optionListNames', [])):
                if oln not in option_list_names:
                    suggestion = get_close_matches(oln, list(option_list_names), n=1)
                    errors.append({
                        'type': 'INVALID_REFERENCE',
                        'path': f'{path}.sku.optionListNames[{j}]',
                        'message': f'Option list "{oln}" not found',
                        'suggestion': suggestion[0] if suggestion else None
                    })

        # Check image URL
        image_url = p.get('imageUrl', '')
        if image_url:
            if not validate_url(image_url):
                warnings.append({
                    'type': 'INVALID_URL',
                    'path': f'{path}.imageUrl',
                    'message': f'Invalid image URL format for "{p.get("name", i)}"'
                })
            products_with_images += 1
        else:
            products_without_images.append(p.get('name', f'Product {i}'))

    # Check for empty categories
    for cat_name, count in products_per_category.items():
        if count == 0:
            warnings.append({
                'type': 'EMPTY_CATEGORY',
                'message': f'Category "{cat_name}" has no products'
            })

    # Check for option lists with no options
    options_per_list = {name: 0 for name in option_list_names}
    for o in options:
        oln = o.get('optionListName')
        if oln in options_per_list:
            options_per_list[oln] += 1

    for list_name, count in options_per_list.items():
        if count == 0:
            warnings.append({
                'type': 'EMPTY_OPTION_LIST',
                'message': f'Option list "{list_name}" has no options'
            })

    # Add warnings for missing images
    for name in products_without_images:
        warnings.append({
            'type': 'MISSING_IMAGE',
            'message': f'Product "{name}" has no image URL'
        })

    summary = {
        'name': cat.get('name', 'Unknown'),
        'categories': len(categories),
        'option_lists': len(option_lists),
        'options': len(options),
        'products': len(products),
        'products_with_images': products_with_images,
        'products_without_images': len(products_without_images),
    }

    return errors, warnings, summary


def print_report(errors: list, warnings: list, summary: dict):
    """Print validation report."""
    print('=== Catalog Validation Report ===\n')
    print(f'Catalog: {summary.get("name", "Unknown")}\n')

    if not errors:
        print('✓ Schema Validation: PASSED')
        print('✓ Referential Integrity: PASSED')
        print('✓ Uniqueness Checks: PASSED')
        print('✓ Naming Conventions: PASSED')
    else:
        # Group errors by type
        error_types = {}
        for e in errors:
            t = e['type']
            if t not in error_types:
                error_types[t] = []
            error_types[t].append(e)

        for error_type, type_errors in error_types.items():
            print(f'✗ {error_type}: {len(type_errors)} error(s)')
            for e in type_errors[:5]:  # Show first 5
                msg = f"  - {e['message']}"
                if e.get('path'):
                    msg = f"  - [{e['path']}] {e['message']}"
                if e.get('suggestion'):
                    msg += f" (Did you mean \"{e['suggestion']}\"?)"
                print(msg)
            if len(type_errors) > 5:
                print(f"  ... and {len(type_errors) - 5} more")

    if warnings:
        print(f'\n⚠ Warnings ({len(warnings)}):')
        for w in warnings[:10]:  # Show first 10
            print(f"  - {w['message']}")
        if len(warnings) > 10:
            print(f"  ... and {len(warnings) - 10} more")

    print(f'\nSummary:')
    print(f"  Categories: {summary.get('categories', 0)}")
    print(f"  Option Lists: {summary.get('option_lists', 0)}")
    print(f"  Options: {summary.get('options', 0)}")
    print(f"  Products: {summary.get('products', 0)}")

    if summary.get('products', 0) > 0:
        pct = round(100 * summary['products_with_images'] / summary['products'])
        print(f"  Products with images: {summary['products_with_images']} ({pct}%)")
        print(f"  Products without images: {summary['products_without_images']}")

    print()
    if errors:
        print(f'Overall: INVALID ({len(errors)} errors, {len(warnings)} warnings)')
    elif warnings:
        print(f'Overall: VALID (with {len(warnings)} warnings)')
    else:
        print('Overall: VALID')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)

    path = sys.argv[1]

    if not Path(path).exists():
        print(f'Error: File not found: {path}')
        sys.exit(2)

    try:
        catalog = load_catalog(path)
    except json.JSONDecodeError as e:
        print(f'Error: Invalid JSON: {e}')
        sys.exit(2)

    errors, warnings, summary = validate_catalog(catalog)
    print_report(errors, warnings, summary)

    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
