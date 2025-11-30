# Documentation Maintenance Guide

This document describes the process for maintaining and updating the AIECS user documentation.

## Overview

The user-facing documentation in `docs/user/` consists of 143+ Markdown files that must be:
- **English-only**: No Chinese content allowed
- **Link-valid**: All internal links must point to existing files
- **Up-to-date**: Code examples and API references must match the current codebase
- **Complete**: All files must be included in the Sphinx build via `index.rst`

## Quality Assurance Tools

### check_documentation.py

The `docs/check_documentation.py` script validates documentation quality:

```bash
cd docs

# Check for Chinese content and broken links
python check_documentation.py

# Check only for broken links
python check_documentation.py --links-only

# Check only for Chinese content
python check_documentation.py --chinese-only

# Save results to file
python check_documentation.py --output check_results.txt
```

**Exit Codes:**
- `0`: No issues found
- `1`: Issues detected (Chinese content, broken links, or errors)

## Translation Process

### When to Translate

If you encounter Chinese content in user documentation:

1. **Identify the file**: Run `check_documentation.py` to find files with Chinese content
2. **Review context**: Understand the technical meaning and context
3. **Translate accurately**: Preserve technical terminology and code examples
4. **Maintain formatting**: Keep markdown formatting, code blocks, and structure intact
5. **Verify links**: Ensure internal links remain valid after translation
6. **Test build**: Run `make html` to verify the file builds correctly

### Translation Guidelines

- **Preserve technical terms**: Keep class names, method names, and API references unchanged
- **Maintain code examples**: Code blocks should remain exactly as-is
- **Keep structure**: Preserve headings, lists, tables, and formatting
- **Fix links**: Update any broken links discovered during translation
- **Verify accuracy**: Ensure technical accuracy matches the codebase

## Link Maintenance

### Link Types

1. **Relative links**: `./FILE.md`, `../PARENT/FILE.md`
2. **Developer docs**: `../../developer/DIR/FILE.md`
3. **External links**: `https://example.com` (not validated)
4. **Anchor links**: `FILE.md#section` (anchor validation skipped)

### Fixing Broken Links

When `check_documentation.py` reports broken links:

1. **Identify the broken link**: Check the file and line number
2. **Find the correct path**: Locate the target file in the documentation structure
3. **Update the link**: Fix the relative path
4. **Verify**: Run `check_documentation.py --links-only` again

### Common Link Issues

- **Moved files**: Update paths when files are moved or renamed
- **Missing files**: Create the file or remove the link
- **Wrong extension**: Ensure `.md` extension is correct
- **Case sensitivity**: Match exact case of filenames
- **Developer docs**: Use `../../developer/` prefix for developer documentation

## Adding New Documentation

### Step-by-Step Process

1. **Create the file**: Add `.md` file in appropriate `docs/user/` subdirectory
2. **Write content**: Use Markdown format, English only
3. **Add to index.rst**: Add file reference to appropriate toctree section
   - Format: `user/DIRECTORY/FILENAME` (without `.md` extension)
4. **Test locally**: Run `make html` to verify build
5. **Quality check**: Run `check_documentation.py`
6. **Verify links**: Ensure all internal links are valid

### Example: Adding a New Tool Documentation

```bash
# 1. Create the file
touch docs/user/TOOLS/NEW_TOOL.md

# 2. Add content (in English, with proper links)

# 3. Edit docs/index.rst - add to Tools section:
#    user/TOOLS/NEW_TOOL

# 4. Test build
cd docs
make html

# 5. Quality check
python check_documentation.py
```

## Updating Existing Documentation

### When to Update

- **API changes**: Update code examples when APIs change
- **New features**: Document new functionality
- **Bug fixes**: Update examples if bugs are fixed
- **Deprecations**: Mark deprecated features appropriately

### Update Checklist

- [ ] Review current content for accuracy
- [ ] Update code examples to match current API
- [ ] Verify import statements are correct
- [ ] Check all internal links still work
- [ ] Run `check_documentation.py` to verify quality
- [ ] Test documentation build: `make html`
- [ ] Review generated HTML for formatting issues

## Code Synchronization

### API Reference Updates

When APIs change:

1. **Update method signatures**: Ensure documented signatures match code
2. **Update examples**: Code examples must use current API
3. **Update imports**: Verify import paths are correct
4. **Check parameters**: Ensure parameter names and types match

### Example Update Process

```python
# Old documentation (incorrect)
from aiecs.tools import BaseTool  # Wrong import path

# Updated documentation (correct)
from aiecs.tools.base_tool import BaseTool  # Correct import path
```

## Build Verification

### Local Build

```bash
cd docs
make clean
make html
```

**Check for:**
- Build errors or warnings
- Missing files
- Broken navigation
- Formatting issues

### Read the Docs Build

The documentation is automatically built on Read the Docs. Configuration is in `.readthedocs.yaml`.

**Verify:**
- Build succeeds without errors
- All pages render correctly
- Navigation works properly
- Search functionality works

## File Organization

### Directory Structure

```
docs/user/
├── APPLICATION/          # Application layer
├── CONFIG/               # Configuration
├── CORE/                 # Core interfaces
├── DOMAIN_AGENT/         # Agent domain
├── DOMAIN_COMMUNITY/     # Community domain
├── DOMAIN_CONTEXT/       # Context domain
├── DOMAIN_EXECUTION/     # Execution domain
├── DOMAIN_TASK/          # Task domain
├── INFRASTRUCTURE_*/     # Infrastructure modules
├── LLM/                  # LLM integration
├── TASKS/                # Task execution
├── TOOLS/                # Tool framework
├── TOOLS_USED_INSTRUCTION/  # Tool usage
├── UTILS/                # Utilities
└── knowledge_graph/      # Knowledge graph
```

### Naming Conventions

- **File names**: UPPER_SNAKE_CASE.md
- **Links**: Use relative paths, preserve case
- **References**: Match exact filenames (case-sensitive)

## Troubleshooting

### Build Failures

**Issue**: Sphinx build fails
- **Solution**: Check `conf.py` configuration
- **Solution**: Verify all referenced files exist
- **Solution**: Check for syntax errors in `.rst` files

### Missing Files in Build

**Issue**: File exists but not in build
- **Solution**: Verify file is listed in `index.rst`
- **Solution**: Check file path matches exactly (case-sensitive)
- **Solution**: Ensure file is in `docs/user/` directory

### Broken Links After Move

**Issue**: Links broken after file reorganization
- **Solution**: Run `check_documentation.py --links-only`
- **Solution**: Update all relative paths
- **Solution**: Rebuild and verify

## Regular Maintenance Tasks

### Monthly

- [ ] Run `check_documentation.py` to check for issues
- [ ] Review and fix any broken links
- [ ] Verify build still works: `make html`

### Before Releases

- [ ] Complete quality check: `check_documentation.py`
- [ ] Verify all API references are current
- [ ] Test full documentation build
- [ ] Review Read the Docs build logs

### After Code Changes

- [ ] Update affected documentation
- [ ] Verify code examples still work
- [ ] Check for new broken links
- [ ] Run quality checks

## Resources

- **Sphinx Documentation**: https://www.sphinx-doc.org/
- **MyST Parser**: https://myst-parser.readthedocs.io/
- **Read the Docs**: https://readthedocs.org/
- **Markdown Guide**: https://www.markdownguide.org/

## Support

For questions or issues with documentation maintenance:
- Check existing documentation in `docs/user/`
- Review `docs/README.md` for build instructions
- Run `check_documentation.py` to identify issues
- Review build logs for specific errors

