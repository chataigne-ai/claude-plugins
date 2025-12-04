# Claude Code Plugins

Custom plugins for Claude Code to support Chataigne development workflows.

## Installation

```shell
# Add the marketplace
/plugin marketplace add ubernion/claude-plugins

# Install plugins
/plugin install catalog-builder@ubernion
```

## Available Plugins

### catalog-builder

Extract restaurant menus and images from websites and Uber Eats to create Chataigne catalog JSON files.

**Commands:**
- `/catalog-builder:create` - Guided workflow to create a catalog
- `/catalog-builder:extract-images` - Extract images from Uber Eats
- `/catalog-builder:validate` - Validate catalog JSON files

**Skills:**
- Catalog schema knowledge
- Image extraction techniques

**Agent:**
- `catalog-validator` - Autonomous catalog validation

[See full documentation](./catalog-builder/README.md)

## Adding New Plugins

1. Create a new directory: `mkdir my-plugin`
2. Add plugin manifest: `my-plugin/.claude-plugin/plugin.json`
3. Add components (commands/, agents/, skills/, hooks/)
4. Update `.claude-plugin/marketplace.json` to include the new plugin
5. Push to GitHub

## License

MIT
