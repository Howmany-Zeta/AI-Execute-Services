# Python Middleware Dependency Checker

This directory contains scripts for analyzing and managing dependencies in the python-middleware project.

## Scripts

### `dependency_checker.py`

A comprehensive dependency analysis tool that scans all Python files in the project to identify imported packages and compare them against the current `pyproject.toml` configuration.

#### Features

- **Automatic Import Detection**: Uses AST parsing to extract all import statements from Python files
- **Dependency Categorization**: Distinguishes between runtime and development dependencies
- **Missing Dependency Detection**: Identifies packages that are imported but not listed in `pyproject.toml`
- **Package Name Mapping**: Maps import names to their corresponding package names (e.g., `cv2` → `opencv-python`)
- **Standard Library Filtering**: Excludes Python standard library modules from the analysis
- **Comprehensive Reporting**: Generates detailed reports with file locations and recommendations

#### Usage

```bash
# Run from the python-middleware directory
python3 scripts/dependency_checker.py

# Or specify a custom project path
python3 scripts/dependency_checker.py /path/to/python-middleware
```

#### Output

The script generates:
1. **Console Output**: Detailed dependency analysis printed to the terminal
2. **Report File**: `scripts/dependency_report.txt` with the complete analysis

#### Report Sections

1. **🔧 Runtime Dependencies**: Dependencies needed for the application to run
2. **🛠️ Development Dependencies**: Dependencies needed only for development/testing
3. **📊 Summary**: Statistics about found and missing dependencies
4. **📝 Missing Dependencies**: Formatted lists ready to add to `pyproject.toml`
5. **💡 Recommendations**: Suggestions for potentially unused dependencies
6. **⚠️ Special Notes**: Important considerations and limitations

#### Example Output

```
🔧 RUNTIME DEPENDENCIES
----------------------------------------
❌ MISSING fastapi
    └── app/main.py
    └── app/api/stream_router.py

✅ PRESENT pandas
    └── app/tools/pandas_tool.py
    └── app/tools/stats_tool.py
```

#### Configuration

The script includes built-in mappings for common packages. You can extend the `package_mappings` dictionary in the script to add custom mappings:

```python
self.package_mappings = {
    'cv2': 'opencv-python',
    'PIL': 'pillow',
    'yaml': 'pyyaml',
    # Add your custom mappings here
}
```

#### Limitations

- Some packages may be imported dynamically and not detected
- Conditional imports may not be captured in all cases
- Version constraints need to be manually reviewed
- Some imports may be from sub-packages of larger packages

#### Dependencies

The script requires Python 3.7+ and uses only standard library modules:
- `ast` - For parsing Python source code
- `pathlib` - For file system operations
- `re` - For regular expressions
- `tomllib` (Python 3.11+) or manual parsing for older versions

#### Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'tomllib'`
**Solution**: The script automatically falls back to manual TOML parsing for Python versions < 3.11

**Issue**: Permission denied when running the script
**Solution**: Make sure the script is executable: `chmod +x scripts/dependency_checker.py`

**Issue**: Some dependencies not detected
**Solution**: Check if they are imported dynamically or conditionally. You may need to add them manually.

## Contributing

To add new dependency analysis features:

1. Extend the `DependencyAnalyzer` class
2. Add new package mappings to the `package_mappings` dictionary
3. Update the report generation logic in `generate_report()`
4. Test with various Python files to ensure accuracy

## License

This script is part of the python-middleware project and follows the same license terms.
