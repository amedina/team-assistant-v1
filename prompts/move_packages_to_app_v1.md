# Python Code Refactoring: Package/Module Reorganization with Import Management

## Task Overview
I need to reorganize my Python codebase by moving and grouping packages/modules. You must ensure that ALL imports across the entire project continue to work after the changes.

## Package Changes
**FROM:** [List current package structure]
```
agents/
app/
config/
data_ingestion/
utils/
tests/
tools/
```

**TO:** [List desired package structure]
```
app/
    agents/
    config/
    data_ingestion/
    utils/
    tools/
tests/
```

## Requirements

### 1. Discovery Phase
- **Scan the entire project** for import statements, including:
  - Python imports: `import`, `from ... import`, `importlib`
  - Dynamic imports: `__import__()`, `importlib.import_module()`
  - String-based imports in config/factory patterns
  - Entry points in [@pyproject.toml]
  - Package references in test files and scripts

### 2. Analysis Phase
Before making any changes:
- List ALL files that reference the packages/modules being moved
- Identify import patterns used (absolute vs relative imports)
- Check for dynamic imports or programmatic module loading
- Note any custom import hooks or module finders
- Examine `__init__.py` files and their import/export patterns
- Check `sys.path` modifications or PYTHONPATH dependencies

### 3. Execution Phase
- Move the packages to their new locations
- Update ALL import statements to reflect new module paths
- Update/create `__init__.py` files to maintain package structure
- Update configuration files [@pyproject.toml`]
- Update any entry points or script references
- Ensure proper `__all__` declarations are maintained

### 4. Validation Phase
- Verify that no broken imports remain (`python -m py_compile` for syntax)
- Check that `python -c "import your_module"` works for affected modules
- Run your test suite to ensure no import errors
- Verify that entry points and scripts still work
- Confirm that `uv run` commands execute properly
- Check that any deployed/packaged versions will work

## File Types to Examine
Search these file extensions (don't limit to just these):
- Python source: `.py`, `.pyx`, `.pyi` (type stubs)
- Configuration: `pyproject.toml`
- UV specific: `uv.lock`, any UV workspace configurations
- Documentation: `.md`, `.rst`, `.txt` (may contain code examples)
- Scripts: Shell scripts, batch files that reference modules

## Safety Measures
3. **Use absolute imports** where possible for cleaner module references
4. **Test incrementally** - move one package at a time if the change is complex
5. **Maintain `__init__.py` files** to preserve package structure

## Output Format
Provide:
1. **Analysis Summary**: List of all files that will be modified
2. **Execution Plan**: Step-by-step changes to be made
3. **Modified Files**: Show before/after for each file with import changes
4. **Configuration Updates**: Any config files that need updating
5. **Verification Steps**: How to test that everything still works

## Project Context
- **Framework**: Pure Python
- **Package Manager**: UV
- **Project Structure**:Application
- **Python Version**: 3.11+
- **Package Distribution**: UV
- **Import Style**: Absolute imports preferred
- **Entry Points**: CLI commands, web app

## Special Considerations
- Watch for `__init__.py` files that import and re-export modules
- Check for any hardcoded module paths in string literals
- Consider impact on any deployment scripts or Docker configurations
- Verify that `uv` workspace configurations still work correctly
- Check for any `sys.path` manipulations that might break
- Ensure that any package metadata (version, author, etc.) remains accessible
- Consider namespace packages and their import behavior

**Important**: Do NOT make any changes until you've shown me the complete analysis and execution plan. I want to review everything before proceeding.