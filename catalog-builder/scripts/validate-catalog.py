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
import re
from pathlib import Path
from typing import Any
from difflib import get_close_matches


# Regex for UPPERCASE_SNAKE_CASE validation
REF_PATTERN = re.compile(r'^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$')


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

        # Core structure validation (mirrors catalog-import.service.ts)
        self._validate_catalog_name()
        self._validate_option_list_references_in_options()
        self._validate_category_references_in_products()
        self._validate_option_list_references_in_products()
        self._validate_category_references_in_deals()
        self._validate_product_references_in_deals()
        self._validate_deal_structure()
        self._validate_primary_categories_in_settings()
        self._validate_discount_product_references()
        self._validate_discount_structure()

        # Structure validation for entities
        self._validate_category_structure()
        self._validate_option_list_structure()
        self._validate_option_structure()
        self._validate_product_structure()

        # Uniqueness constraints (from schema-rules.md)
        self._validate_uniqueness()

        # Ref format validation (UPPERCASE_SNAKE_CASE)
        self._validate_ref_format()

        # Option list business rules
        self._validate_option_list_selections()

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

        for opt in catalog.get('options', []):
            ref_name = opt.get('optionListName')
            if ref_name and ref_name not in option_list_names:
                similar = get_close_matches(ref_name, list(option_list_names), n=1, cutoff=0.6)
                suggestion = f' (vouliez-vous dire "{similar[0]}"?)' if similar else ''
                self.errors.append(
                    f'Option list "{ref_name}" référencée dans les options mais non définie{suggestion}'
                )

    def _validate_category_references_in_products(self):
        """4. Validate category references in products"""
        catalog = self.catalog_json.get('catalog', {})

        category_names = set(
            cat.get('name') for cat in catalog.get('categories', [])
            if cat.get('name')
        )

        for prod in catalog.get('products', []):
            ref_name = prod.get('categoryName')
            if ref_name and ref_name not in category_names:
                similar = get_close_matches(ref_name, list(category_names), n=1, cutoff=0.6)
                suggestion = f' (vouliez-vous dire "{similar[0]}"?)' if similar else ''
                self.errors.append(
                    f'Catégorie "{ref_name}" référencée dans le produit "{prod.get("name", "?")}" mais non définie{suggestion}'
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
                    similar = get_close_matches(ref_name, list(option_list_names), n=1, cutoff=0.6)
                    suggestion = f' (vouliez-vous dire "{similar[0]}"?)' if similar else ''
                    self.errors.append(
                        f'Option list "{ref_name}" référencée dans le produit "{product.get("name", "?")}" mais non définie{suggestion}'
                    )

    def _validate_category_references_in_deals(self):
        """6. Validate category references in deals"""
        catalog = self.catalog_json.get('catalog', {})

        category_names = set(
            cat.get('name') for cat in catalog.get('categories', [])
            if cat.get('name')
        )

        for deal in catalog.get('deals', []):
            ref_name = deal.get('categoryName')
            if ref_name and ref_name not in category_names:
                similar = get_close_matches(ref_name, list(category_names), n=1, cutoff=0.6)
                suggestion = f' (vouliez-vous dire "{similar[0]}"?)' if similar else ''
                self.errors.append(
                    f'Catégorie "{ref_name}" référencée dans le deal "{deal.get("name", "?")}" mais non définie{suggestion}'
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
                        similar = get_close_matches(product_name, list(product_names), n=1, cutoff=0.6)
                        suggestion = f' (vouliez-vous dire "{similar[0]}"?)' if similar else ''
                        self.errors.append(
                            f'Produit "{product_name}" référencé dans le deal "{deal_name}" mais non défini{suggestion}'
                        )

    def _validate_deal_structure(self):
        """
        7b. Validate deal structure and required fields.

        Each deal must have:
        - name (string, required)
        - categoryName (string, required, must reference existing category)
        - price (object with amount and currency, required)
        - lines (array, required, at least 1 line)
        - Each line must have skus array with at least 1 sku
        - Each sku must have skuName (string, required)
        """
        catalog = self.catalog_json.get('catalog', {})

        for i, deal in enumerate(catalog.get('deals', [])):
            deal_name = deal.get('name') or f'Deal #{i+1}'

            # Required: name
            if not deal.get('name'):
                self.errors.append(f'Deal #{i+1}: "name" est requis')

            # Required: categoryName
            if not deal.get('categoryName'):
                self.errors.append(f'Deal "{deal_name}": "categoryName" est requis')

            # Required: price
            price = deal.get('price')
            if not price:
                self.errors.append(f'Deal "{deal_name}": "price" est requis')
            elif not isinstance(price, dict):
                self.errors.append(f'Deal "{deal_name}": "price" doit être un objet {{amount, currency}}')
            elif 'amount' not in price or 'currency' not in price:
                self.errors.append(f'Deal "{deal_name}": "price" doit avoir "amount" et "currency"')

            # Required: lines
            lines = deal.get('lines')
            if not lines:
                self.errors.append(f'Deal "{deal_name}": "lines" est requis (au moins 1 ligne)')
            elif not isinstance(lines, list):
                self.errors.append(f'Deal "{deal_name}": "lines" doit être un tableau')
            elif len(lines) == 0:
                self.errors.append(f'Deal "{deal_name}": "lines" doit contenir au moins 1 ligne')
            else:
                for j, line in enumerate(lines):
                    skus = line.get('skus')
                    if not skus:
                        self.errors.append(f'Deal "{deal_name}", ligne #{j+1}: "skus" est requis')
                    elif not isinstance(skus, list):
                        self.errors.append(f'Deal "{deal_name}", ligne #{j+1}: "skus" doit être un tableau')
                    elif len(skus) == 0:
                        self.errors.append(f'Deal "{deal_name}", ligne #{j+1}: "skus" doit contenir au moins 1 sku')
                    else:
                        for k, sku in enumerate(skus):
                            if not sku.get('skuName'):
                                self.errors.append(f'Deal "{deal_name}", ligne #{j+1}, sku #{k+1}: "skuName" est requis')

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
                similar = get_close_matches(primary_category, list(category_names), n=1, cutoff=0.6)
                suggestion = f' (vouliez-vous dire "{similar[0]}"?)' if similar else ''
                self.errors.append(
                    f'Catégorie primaire "{primary_category}" référencée dans les paramètres mais non définie{suggestion}'
                )

    def _validate_discount_product_references(self):
        """
        9. Validate product references in discounts.

        Mirrors the discount validation from catalog-import.service.ts:
        - BOGO discounts reference products by name (productNames array)
        - Free product discounts reference a single product (productName)
        """
        catalog = self.catalog_json.get('catalog', {})

        product_names = set(
            prod.get('name') for prod in catalog.get('products', [])
            if prod.get('name')
        )

        for discount in catalog.get('discounts', []):
            discount_name = discount.get('name', 'Unknown')
            discount_type = discount.get('discountType')
            discount_data = discount.get('discountData', {})

            # BOGO discounts have productNames array
            if discount_type == 'bogo' and 'productNames' in discount_data:
                for product_name in discount_data.get('productNames', []):
                    if product_name not in product_names:
                        similar = get_close_matches(product_name, list(product_names), n=1, cutoff=0.6)
                        suggestion = f' (vouliez-vous dire "{similar[0]}"?)' if similar else ''
                        self.errors.append(
                            f'Produit "{product_name}" référencé dans la réduction BOGO "{discount_name}" mais non défini{suggestion}'
                        )

            # Free product discounts have productName string
            if discount_type == 'free_product' and 'productName' in discount_data:
                product_name = discount_data.get('productName')
                if product_name and product_name not in product_names:
                    similar = get_close_matches(product_name, list(product_names), n=1, cutoff=0.6)
                    suggestion = f' (vouliez-vous dire "{similar[0]}"?)' if similar else ''
                    self.errors.append(
                        f'Produit "{product_name}" référencé dans la réduction "{discount_name}" mais non défini{suggestion}'
                    )

    def _validate_discount_structure(self):
        """
        9b. Validate discount structure and required fields.

        Discount types and their required discountData:
        - percentage: { percentage: number, maxDiscountAmount?: number }
        - fixed: { amount: number }
        - free_product: { productName: string } or { productId: string }
        - bogo: { productNames: string[] } or { productIds: string[] }
        - free_shipping: {} (no additional data needed)

        All discounts have:
        - name (required)
        - discountType (required, one of the above)
        - level (required, "pushed" | "public" | "hidden")
        """
        catalog = self.catalog_json.get('catalog', {})
        valid_discount_types = {'percentage', 'fixed', 'free_product', 'bogo', 'free_shipping'}
        valid_levels = {'pushed', 'public', 'hidden'}

        for i, discount in enumerate(catalog.get('discounts', [])):
            discount_name = discount.get('name') or f'Discount #{i+1}'

            # Required: name
            if not discount.get('name'):
                self.errors.append(f'Discount #{i+1}: "name" est requis')

            # Required: discountType
            discount_type = discount.get('discountType')
            if not discount_type:
                self.errors.append(f'Discount "{discount_name}": "discountType" est requis')
            elif discount_type not in valid_discount_types:
                self.errors.append(
                    f'Discount "{discount_name}": "discountType" invalide "{discount_type}" '
                    f'(valides: {", ".join(sorted(valid_discount_types))})'
                )

            # Required: level
            level = discount.get('level')
            if not level:
                self.errors.append(f'Discount "{discount_name}": "level" est requis')
            elif level not in valid_levels:
                self.errors.append(
                    f'Discount "{discount_name}": "level" invalide "{level}" '
                    f'(valides: {", ".join(sorted(valid_levels))})'
                )

            # Validate discountData based on type
            discount_data = discount.get('discountData', {})

            if discount_type == 'percentage':
                if 'percentage' not in discount_data:
                    self.errors.append(f'Discount "{discount_name}": discountData.percentage est requis pour type "percentage"')
                elif not isinstance(discount_data.get('percentage'), (int, float)):
                    self.errors.append(f'Discount "{discount_name}": discountData.percentage doit être un nombre')
                elif discount_data.get('percentage', 0) <= 0 or discount_data.get('percentage', 0) > 100:
                    self.warnings.append(f'Discount "{discount_name}": percentage devrait être entre 1 et 100')

            elif discount_type == 'fixed':
                if 'amount' not in discount_data:
                    self.errors.append(f'Discount "{discount_name}": discountData.amount est requis pour type "fixed"')
                elif not isinstance(discount_data.get('amount'), (int, float)):
                    self.errors.append(f'Discount "{discount_name}": discountData.amount doit être un nombre')

            elif discount_type == 'free_product':
                if 'productName' not in discount_data and 'productId' not in discount_data:
                    self.errors.append(f'Discount "{discount_name}": discountData.productName est requis pour type "free_product"')

            elif discount_type == 'bogo':
                if 'productNames' not in discount_data and 'productIds' not in discount_data:
                    self.errors.append(f'Discount "{discount_name}": discountData.productNames est requis pour type "bogo"')

    def _validate_uniqueness(self):
        """
        10. Validate uniqueness constraints.

        From schema-rules.md:
        - category.ref must be unique
        - category.name must be unique
        - optionList.ref must be unique
        - optionList.name must be unique
        - option.ref must be unique
        """
        catalog = self.catalog_json.get('catalog', {})

        # Category refs
        category_refs = [cat.get('ref') for cat in catalog.get('categories', []) if cat.get('ref')]
        self._check_duplicates(category_refs, 'ref de catégorie')

        # Category names
        category_names = [cat.get('name') for cat in catalog.get('categories', []) if cat.get('name')]
        self._check_duplicates(category_names, 'nom de catégorie')

        # Option list refs
        ol_refs = [ol.get('ref') for ol in catalog.get('optionLists', []) if ol.get('ref')]
        self._check_duplicates(ol_refs, "ref de liste d'options")

        # Option list names
        ol_names = [ol.get('name') for ol in catalog.get('optionLists', []) if ol.get('name')]
        self._check_duplicates(ol_names, "nom de liste d'options")

        # Option refs
        option_refs = [opt.get('ref') for opt in catalog.get('options', []) if opt.get('ref')]
        self._check_duplicates(option_refs, "ref d'option")

        # Product refs (if present)
        product_refs = [prod.get('ref') for prod in catalog.get('products', []) if prod.get('ref')]
        self._check_duplicates(product_refs, 'ref de produit')

    def _check_duplicates(self, values: list[str], entity_type: str):
        """Helper to find and report duplicates"""
        seen = set()
        for value in values:
            if value in seen:
                self.errors.append(f'{entity_type.capitalize()} dupliqué: "{value}"')
            seen.add(value)

    def _validate_ref_format(self):
        """
        11. Validate ref format (UPPERCASE_SNAKE_CASE).

        Pattern: ^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$
        Valid: PIZZA_TOPPINGS, MAIN_COURSES, EXTRA_CHEESE
        Invalid: pizza-toppings, MainCourses, extra cheese
        """
        catalog = self.catalog_json.get('catalog', {})

        # Check category refs
        for cat in catalog.get('categories', []):
            ref = cat.get('ref')
            if ref and not REF_PATTERN.match(ref):
                suggested = self._suggest_ref(ref)
                self.warnings.append(
                    f'Ref de catégorie "{ref}" ne suit pas UPPERCASE_SNAKE_CASE (suggestion: {suggested})'
                )

        # Check option list refs
        for ol in catalog.get('optionLists', []):
            ref = ol.get('ref')
            if ref and not REF_PATTERN.match(ref):
                suggested = self._suggest_ref(ref)
                self.warnings.append(
                    f"Ref de liste d'options \"{ref}\" ne suit pas UPPERCASE_SNAKE_CASE (suggestion: {suggested})"
                )

        # Check option refs
        for opt in catalog.get('options', []):
            ref = opt.get('ref')
            if ref and not REF_PATTERN.match(ref):
                suggested = self._suggest_ref(ref)
                self.warnings.append(
                    f'Ref d\'option "{ref}" ne suit pas UPPERCASE_SNAKE_CASE (suggestion: {suggested})'
                )

        # Check product refs
        for prod in catalog.get('products', []):
            ref = prod.get('ref')
            if ref and not REF_PATTERN.match(ref):
                suggested = self._suggest_ref(ref)
                self.warnings.append(
                    f'Ref de produit "{ref}" ne suit pas UPPERCASE_SNAKE_CASE (suggestion: {suggested})'
                )

    def _suggest_ref(self, value: str) -> str:
        """Convert a string to UPPERCASE_SNAKE_CASE suggestion"""
        # Replace common separators with underscores
        result = re.sub(r'[-\s]+', '_', value)
        # Insert underscore before uppercase letters (for camelCase)
        result = re.sub(r'([a-z])([A-Z])', r'\1_\2', result)
        # Convert to uppercase and clean up
        result = result.upper()
        # Remove any non-alphanumeric characters except underscores
        result = re.sub(r'[^A-Z0-9_]', '', result)
        # Remove consecutive underscores
        result = re.sub(r'_+', '_', result)
        # Remove leading/trailing underscores
        result = result.strip('_')
        return result or 'UNNAMED'

    def _validate_product_structure(self):
        """
        12. Validate product structure and required fields.

        Each product must have:
        - name (string, required)
        - categoryName (string, required)
        - sku (object, required)
        - sku.price (object with amount and currency, required)
        """
        catalog = self.catalog_json.get('catalog', {})

        for i, prod in enumerate(catalog.get('products', [])):
            prod_name = prod.get('name') or f'Product #{i+1}'

            # Required: name
            if not prod.get('name'):
                self.errors.append(f'Product #{i+1}: "name" est requis')

            # Required: categoryName
            if not prod.get('categoryName'):
                self.errors.append(f'Product "{prod_name}": "categoryName" est requis')

            # Required: sku
            sku = prod.get('sku')
            if not sku:
                self.errors.append(f'Product "{prod_name}": "sku" est requis')
            elif not isinstance(sku, dict):
                self.errors.append(f'Product "{prod_name}": "sku" doit être un objet')

    def _validate_option_structure(self):
        """
        13. Validate option structure and required fields.

        Each option must have:
        - name (string, required)
        - optionListName (string, required)
        - price (object with amount and currency, required)
        """
        catalog = self.catalog_json.get('catalog', {})

        for i, opt in enumerate(catalog.get('options', [])):
            opt_name = opt.get('name') or f'Option #{i+1}'

            # Required: name
            if not opt.get('name'):
                self.errors.append(f'Option #{i+1}: "name" est requis')

            # Required: optionListName
            if not opt.get('optionListName'):
                self.errors.append(f'Option "{opt_name}": "optionListName" est requis')

            # Required: price
            price = opt.get('price')
            if price is None:
                self.errors.append(f'Option "{opt_name}": "price" est requis')

    def _validate_category_structure(self):
        """
        14. Validate category structure and required fields.

        Each category must have:
        - name (string, required)
        """
        catalog = self.catalog_json.get('catalog', {})

        for i, cat in enumerate(catalog.get('categories', [])):
            # Required: name
            if not cat.get('name'):
                self.errors.append(f'Category #{i+1}: "name" est requis')

    def _validate_option_list_structure(self):
        """
        15. Validate option list structure and required fields.

        Each option list must have:
        - name (string, required)
        """
        catalog = self.catalog_json.get('catalog', {})

        for i, ol in enumerate(catalog.get('optionLists', [])):
            # Required: name
            if not ol.get('name'):
                self.errors.append(f'Option list #{i+1}: "name" est requis')

    def _validate_option_list_selections(self):
        """
        16. Validate option list selection constraints.

        Business rules:
        - minSelections must be >= 0
        - maxSelections must be >= minSelections (or null for unlimited)
        - If minSelections > 0, option list should have enough options
        """
        catalog = self.catalog_json.get('catalog', {})

        # Build map of option list name -> option count
        option_counts: dict[str, int] = {}
        for opt in catalog.get('options', []):
            ol_name = opt.get('optionListName')
            if ol_name:
                option_counts[ol_name] = option_counts.get(ol_name, 0) + 1

        for ol in catalog.get('optionLists', []):
            ol_name = ol.get('name', 'Unknown')
            min_sel = ol.get('minSelections')
            max_sel = ol.get('maxSelections')

            # Check minSelections is non-negative
            if min_sel is not None and min_sel < 0:
                self.errors.append(
                    f"Liste d'options \"{ol_name}\": minSelections doit être >= 0 (actuel: {min_sel})"
                )

            # Check maxSelections >= minSelections (if both defined and max is not null)
            if min_sel is not None and max_sel is not None:
                if max_sel < min_sel:
                    self.errors.append(
                        f"Liste d'options \"{ol_name}\": maxSelections ({max_sel}) doit être >= minSelections ({min_sel})"
                    )

            # Check there are enough options for required selections
            if min_sel is not None and min_sel > 0:
                num_options = option_counts.get(ol_name, 0)
                if num_options < min_sel:
                    self.warnings.append(
                        f"Liste d'options \"{ol_name}\": minSelections={min_sel} mais seulement {num_options} option(s) définies"
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
