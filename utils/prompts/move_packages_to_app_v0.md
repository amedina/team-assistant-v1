# Code Refactoring: Folder Reorganization with Import Management

## Task Overview
I need to reorganize my codebase by moving and grouping folders. You must ensure that ALL imports across the entire project continue to work after the changes.

## Folder Changes
**FROM:**
```
agents/
app/
config/
data_ingestion/
utils/
tests/
```

**TO:**
```
app/
    agents/
    config/
    data_ingestion/
    utils/
tests/
```

## Requirements

### 1. Discovery Phase
- **Scan the entire project** for import statements, including:
  - JavaScript/TypeScript: `import`, `require()`, `export`
  - CSS: `@import`, `url()`
  - HTML: `<script src>`, `<link href>`
  - Config files: webpack, vite, tsconfig paths, etc.
  - Package.json scripts and dependencies
  - Any framework-specific imports (Next.js, React, etc.)

### 2. Analysis Phase
Before making any changes:
- List ALL files that reference the folders being moved
- Identify the types of import patterns used (relative vs absolute paths)
- Check for dynamic imports or programmatic path construction
- Note any path aliases or module resolution configurations

### 3. Execution Phase
- Move the folders to their new locations
- Update ALL import statements to reflect new paths
- Update any configuration files (tsconfig.json, webpack.config.js, etc.)
- Preserve any existing path aliases by updating their configurations

### 4. Validation Phase
- Verify that no broken imports remain
- Check that the project builds successfully
- Ensure no runtime errors related to missing modules
- Confirm that relative path calculations are correct

## File Types to Examine
Search these file extensions (don't limit to just these):
- Source code: `.js`, `.jsx`, `.ts`, `.tsx`, `.vue`, `.svelte`
- Stylesheets: `.css`, `.scss`, `.sass`, `.less`, `.styl`
- Config files: `.json`, `.js`, `.ts`, `.yaml`, `.yml`, `.toml`
- HTML templates: `.html`, `.htm`, `.ejs`, `.hbs`, `.pug`
- Documentation: `.md`, `.mdx` (may contain code examples)

## Safety Measures
1. **Create a backup** or ensure version control is up to date
2. **Show me a preview** of all changes before executing
3. **Use absolute paths** where possible for cleaner imports
4. **Test incrementally** - move one folder at a time if the change is complex

## Output Format
Provide:
1. **Analysis Summary**: List of all files that will be modified
2. **Execution Plan**: Step-by-step changes to be made
3. **Modified Files**: Show before/after for each file with import changes
4. **Configuration Updates**: Any config files that need updating
5. **Verification Steps**: How to test that everything still works

## Project Context
- **Framework/Stack**: [Your framework - React, Vue, Angular, etc.]
- **Build Tool**: [Webpack, Vite, Parcel, etc.]
- **Package Manager**: [npm, yarn, pnpm]
- **TypeScript**: [Yes/No]
- **Path Aliases**: [List any existing @ or ~ aliases]
- **Monorepo**: [Yes/No - if yes, specify tool like Lerna, Nx, etc.]

## Special Considerations
- Watch for barrel exports (`index.js` files that re-export)
- Check for any hardcoded paths in comments or documentation
- Consider impact on any CI/CD scripts or deployment configurations
- Verify that any generated files or build outputs reference correct paths

**Important**: Do NOT make any changes until you've shown me the complete analysis and execution plan. I want to review everything before proceeding.