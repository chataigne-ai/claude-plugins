#!/usr/bin/env python3
"""
Chataigne Catalog Validator

Validates catalog JSON files for schema compliance and referential integrity.
This script mirrors the production validation logic from catalog-import.service.ts

Usage:
    python3 validate-catalog.py <catalog_path>

Exit codes:
    0 - Valid
    1 - Invalid (has errors)
    2 - File not found or parse error
"""

import sys
import json
from pathlib import Path
from typing import Any


class CatalogValidator:
    """
    Validates Chataigne catalog JSON files.

    Mirrors the production validation logic from:
    apps/web/shared/lib/catalog-import.service.ts
    """

    def __init__(self, catalog_json: dict):
        self.catalog_json = catalog_json
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self) -> bool:
        """Run all validations. Returns True if valid."""
        self._validate_root_structure()

        if self.errors:
            return False

        self._validate_catalog_name()
        self._validate_option_list_references_in_options()
        self._validate_category_references_in_products()
        self._validate_option_list_references_in_products()
        self._validate_category_references_in_deals()
        self._validate_product_references_in_deals()
        self._validate_primary_categories_in_settings()

        # Additional quality checks (warnings only)
        self._check_images()
        self._check_empty_entities()
        self._check_price_format()

        return len(self.errors) == 0

    def _validate_root_structure(self):
        """1. Validate root structure"""
        if not self.catalog_json.get('catalog'):
            self.errors.append(
                "Structure JSON invalide: propriété 'catalog' manquante"
            )

    def _validate_catalog_name(self):
        """2. Validate catalog name"""
        catalog = self.catalog_json.get('catalog', {})
        name = catalog.get('name', '').strip()
        if not name:
            self.errors.append("Le nom du catalogue est requis")

    def _validate_option_list_references_in_options(self):
        """3. Validate option lists references in options"""
        catalog = self.catalog_json.get('catalog', {})

        option_list_names = set(
            ol.get('name') for ol in catalog.get('optionLists', [])
            if ol.get('name')
        )

        referenced_option_lists = set(
            opt.get('optionListName') for opt in catalog.get('options', [])
            if opt.get('optionListName')
        )

        for ref_name in referenced_option_lists:
            if ref_name not in option_list_names:
                self.errors.append(
                    f'Option list "{ref_name}" référencée dans les options mais non définie'
                )

    def _validate_category_references_in_products(self):
        """4. Validate category references in products"""
        catalog = self.catalog_json.get('catalog', {})

        category_names = set(
            cat.get('name') for cat in catalog.get('categories', [])
            if cat.get('name')
        )

        referenced_categories = set(
            prod.get('categoryName') for prod in catalog.get('products', [])
            if prod.get('categoryName')
        )

        for ref_name in referenced_categories:
            if ref_name not in category_names:
                self.errors.append(
                    f'Catégorie "{ref_name}" référencée dans les produits mais non définie'
                )

    def _validate_option_list_references_in_products(self):
        """5. Validate option list references in products"""
        catalog = self.catalog_json.get('catalog', {})

        option_list_names = set(
            ol.get('name') for ol in catalog.get('optionLists', [])
            if ol.get('name')
        )

        for product in catalog.get('products', []):
            sku = product.get('sku', {})
            for ref_name in sku.get('optionListNames', []):
                if ref_name not in option_list_names:
                    self.errors.append(
                        f'Option list "{ref_name}" référencée dans les produits mais non définie'
                    )

    def _validate_category_references_in_deals(self):
        """6. Validate category references in deals"""
        catalog = self.catalog_json.get('catalog', {})

        category_names = set(
            cat.get('name') for cat in catalog.get('categories', [])
            if cat.get('name')
        )

        deal_categories = set(
            deal.get('categoryName') for deal in catalog.get('deals', [])
            if deal.get('categoryName')
        )

        for ref_name in deal_categories:
            if ref_name not in category_names:
                self.errors.append(
                    f'Catégorie "{ref_name}" référencée dans les deals mais non définie'
                )

    def _validate_product_references_in_deals(self):
        """7. Validate product/sku references in deals"""
        catalog = self.catalog_json.get('catalog', {})

        product_names = set(
            prod.get('name') for prod in catalog.get('products', [])
            if prod.get('name')
        )

        for deal in catalog.get('deals', []):
            deal_name = deal.get('name', 'Unknown')
            for line in deal.get('lines', []):
                for sku in line.get('skus', []):
                    sku_name = sku.get('skuName', '')
                    # skuName can be product name or "ProductName (options)"
                    product_name = sku_name.split(' (')[0]
                    if product_name and product_name not in product_names:
                        self.errors.append(
                            f'Produit "{product_name}" référencé dans le deal "{deal_name}" mais non défini'
                        )

    def _validate_primary_categories_in_settings(self):
        """8. Validate primary categories in settings"""
        catalog = self.catalog_json.get('catalog', {})
        settings = catalog.get('settings', {})

        if not settings:
            return

        category_names = set(
            cat.get('name') for cat in catalog.get('categories', [])
            if cat.get('name')
        )

        for primary_category in settings.get('primaryCategories', []):
            if primary_category not in category_names:
                self.errors.append(
                    f'Catégorie primaire "{primary_category}" référencée dans les paramètres mais non définie'
                )

    # === Additional Quality Checks (Warnings) ===

    def _check_images(self):
        """Check for missing images on products and options"""
        catalog = self.catalog_json.get('catalog', {})

        products_without_images = []
        for prod in catalog.get('products', []):
            if not prod.get('imageUrl'):
                products_without_images.append(prod.get('name', 'Unknown'))

        if products_without_images:
            self.warnings.append(
                f"{len(products_without_images)} produit(s) sans image: {', '.join(products_without_images[:5])}"
                + (f" ... et {len(products_without_images) - 5} autres" if len(products_without_images) > 5 else "")
            )

        options_without_images = []
        for opt in catalog.get('options', []):
            if not opt.get('imageUrl'):
                options_without_images.append(opt.get('name', 'Unknown'))

        if options_without_images:
            self.warnings.append(
                f"{len(options_without_images)} option(s) sans image"
            )

        # Check for duplicate image URLs (causes import issues!)
        self._check_duplicate_image_urls()

    def _check_duplicate_image_urls(self):
        """
        Check for duplicate image URLs across products.

        IMPORTANT: When multiple products share the exact same imageUrl,
        Chataigne's import only assigns the S3 image to ONE product.
        The others end up with no image.

        Workaround: Add unique query params to each URL (e.g., ?p=1, ?p=2)
        """
        catalog = self.catalog_json.get('catalog', {})

        # Collect all image URLs and their products
        url_to_products: dict[str, list[str]] = {}

        for prod in catalog.get('products', []):
            url = prod.get('imageUrl', '')
            if url:
                # Strip existing query params for comparison
                base_url = url.split('?')[0]
                if base_url not in url_to_products:
                    url_to_products[base_url] = []
                url_to_products[base_url].append(prod.get('name', 'Unknown'))

        # Find duplicates
        duplicates = {url: prods for url, prods in url_to_products.items() if len(prods) > 1}

        if duplicates:
            total_affected = sum(len(prods) for prods in duplicates.values())
            self.warnings.append(
                f"⚠️  {len(duplicates)} image URL(s) partagée(s) par {total_affected} produits - "
                f"RISQUE: seul 1 produit par URL recevra l'image lors de l'import! "
                f"Ajoutez des query params uniques (ex: ?p=1, ?p=2) pour éviter ce problème."
            )

            # Show first few duplicates
            for url, prods in list(duplicates.items())[:3]:
                short_url = '...' + url[-40:] if len(url) > 40 else url
                self.warnings.append(
                    f"   → {short_url} utilisée par: {', '.join(prods[:3])}"
                    + (f" +{len(prods)-3} autres" if len(prods) > 3 else "")
                )

    def _check_empty_entities(self):
        """Check for empty categories or option lists"""
        catalog = self.catalog_json.get('catalog', {})

        # Check empty categories
        category_names = set(
            cat.get('name') for cat in catalog.get('categories', [])
        )
        used_categories = set(
            prod.get('categoryName') for prod in catalog.get('products', [])
        )

        empty_categories = category_names - used_categories
        for cat_name in empty_categories:
            self.warnings.append(f'Catégorie "{cat_name}" n\'a aucun produit')

        # Check empty option lists
        option_list_names = set(
            ol.get('name') for ol in catalog.get('optionLists', [])
        )
        used_option_lists = set(
            opt.get('optionListName') for opt in catalog.get('options', [])
        )

        empty_option_lists = option_list_names - used_option_lists
        for ol_name in empty_option_lists:
            self.warnings.append(f'Option list "{ol_name}" n\'a aucune option')

    def _check_price_format(self):
        """Check price format is correct"""
        catalog = self.catalog_json.get('catalog', {})

        # Check product prices
        for prod in catalog.get('products', []):
            sku = prod.get('sku', {})
            price = sku.get('price')
            if price is not None:
                if not isinstance(price, dict):
                    self.errors.append(
                        f'Produit "{prod.get("name")}": price doit être un objet {{amount, currency}}'
                    )
                elif 'amount' not in price or 'currency' not in price:
                    self.errors.append(
                        f'Produit "{prod.get("name")}": price doit avoir amount et currency'
                    )

        # Check option prices
        for opt in catalog.get('options', []):
            price = opt.get('price')
            if price is not None:
                if not isinstance(price, dict):
                    self.errors.append(
                        f'Option "{opt.get("name")}": price doit être un objet {{amount, currency}}'
                    )
                elif 'amount' not in price or 'currency' not in price:
                    self.errors.append(
                        f'Option "{opt.get("name")}": price doit avoir amount et currency'
                    )


def print_report(validator: CatalogValidator, catalog_json: dict):
    """Print validation report"""
    catalog = catalog_json.get('catalog', {})

    print("=" * 55)
    print("  CHATAIGNE CATALOG VALIDATION REPORT")
    print("=" * 55)
    print(f"\n📦 Catalog: {catalog.get('name', 'Unknown')}")

    # Summary stats
    print(f"\n📊 Contents:")
    print(f"   • Categories: {len(catalog.get('categories', []))}")
    print(f"   • Products: {len(catalog.get('products', []))}")
    print(f"   • Option Lists: {len(catalog.get('optionLists', []))}")
    print(f"   • Options: {len(catalog.get('options', []))}")
    print(f"   • Deals: {len(catalog.get('deals', []))}")
    print(f"   • Discounts: {len(catalog.get('discounts', []))}")

    # Errors
    if validator.errors:
        print(f"\n❌ ERRORS ({len(validator.errors)}):")
        for err in validator.errors:
            print(f"   • {err}")
    else:
        print(f"\n✅ No errors found!")

    # Warnings
    if validator.warnings:
        print(f"\n⚠️  WARNINGS ({len(validator.warnings)}):")
        for warn in validator.warnings:
            print(f"   • {warn}")

    # Final verdict
    print("\n" + "=" * 55)
    if validator.errors:
        print("  ❌ INVALID - Fix errors before importing")
    elif validator.warnings:
        print("  ✅ VALID (with warnings)")
    else:
        print("  ✅ VALID - Ready for import!")
    print("=" * 55)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage: python3 validate-catalog.py <path_to_catalog.json>")
        sys.exit(2)

    path = sys.argv[1]

    # Check file exists
    if not Path(path).exists():
        print(f"❌ Error: File not found: {path}")
        sys.exit(2)

    # Load JSON
    try:
        with open(path, 'r', encoding='utf-8') as f:
            catalog_json = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON: {e}")
        sys.exit(2)

    # Validate
    validator = CatalogValidator(catalog_json)
    is_valid = validator.validate()

    # Print report
    print_report(validator, catalog_json)

    # Exit code
    sys.exit(0 if is_valid else 1)


if __name__ == '__main__':
    main()
