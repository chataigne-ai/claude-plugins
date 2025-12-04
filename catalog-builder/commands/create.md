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
- Extract JSON-LD structured data for menu items
- Extract unique image URLs for later correlation

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

**From Uber Eats:**
- Download all unique images to a temp folder
- Use Read tool to visually inspect images
- Ask user to help identify ambiguous images
- Map identified images to products

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

## Important Notes

- Always confirm category structure with user before proceeding
- For Uber Eats, focus on extracting JSON-LD data for accurate pricing
- Exclude alcohol products unless user specifically requests them
- Use UPPERCASE_SNAKE_CASE for all ref fields
- Prices should use EUR currency code (or ask user for currency)
