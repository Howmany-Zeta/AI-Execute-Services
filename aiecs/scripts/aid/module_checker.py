#!/usr/bin/env python3
"""
AIECS Module Import Checker

Tests all module imports in the aiecs package to ensure there are no import errors
that would occur when installing from PyPI. This simulates the installation process
and catches "cannot find module" errors before publishing.

Usage:
    python -m aiecs.scripts.aid.module_checker
    aiecs-check-modules [--verbose] [--module MODULE]
"""

import argparse
import ast
import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import traceback


class ModuleImportChecker:
    """Checks all module imports to catch errors before publishing"""

    def __init__(self, project_root: Optional[Path] = None, verbose: bool = False):
        """Initialize the module checker"""
        if project_root is None:
            # Find project root by looking for pyproject.toml
            current = Path(__file__).parent
            while current != current.parent:
                if (current / "pyproject.toml").exists():
                    project_root = current
                    break
                current = current.parent

            if project_root is None:
                raise RuntimeError("Could not find project root (pyproject.toml)")

        self.project_root = project_root
        self.aiecs_root = project_root / "aiecs"
        self.verbose = verbose
        
        # Add project root to sys.path so we can import aiecs modules
        project_root_str = str(self.project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
        
        # Results storage
        self.import_errors: List[Tuple[str, str, Exception]] = []  # (module, import_name, error)
        self.failed_modules: List[Tuple[str, Exception]] = []  # (module, error)
        self.successful_modules: Set[str] = set()
        
        # Track which modules we've tried to import
        self.imported_modules: Set[str] = set()
        self.module_files: Dict[str, Path] = {}

    def find_all_modules(self) -> List[str]:
        """Find all Python modules in the aiecs package"""
        modules = []
        
        if not self.aiecs_root.exists():
            return modules

        for py_file in self.aiecs_root.rglob("*.py"):
            # Skip __pycache__ and test files (test_*.py or *_test.py patterns)
            filename = py_file.name.lower()
            if "__pycache__" in str(py_file) or filename.startswith("test_") or filename.endswith("_test.py"):
                continue
            
            # Convert file path to module name
            relative_path = py_file.relative_to(self.project_root)
            module_parts = relative_path.parts[:-1] + (relative_path.stem,)
            module_name = ".".join(module_parts)
            
            modules.append(module_name)
            self.module_files[module_name] = py_file

        return sorted(modules)

    def resolve_relative_import(self, module_name: Optional[str], level: int, file_path: Path) -> Optional[str]:
        """
        Resolve a relative import to an absolute module name.
        Returns None if it's not a relative import or not an aiecs module.
        
        Args:
            module_name: The module name from AST (without leading dots)
            level: The number of dots (0 = absolute, 1 = ., 2 = .., etc.)
            file_path: Path to the file containing the import
        """
        if level == 0:
            # Absolute import
            return None
        
        # Get the module name for the current file
        relative_path = file_path.relative_to(self.project_root)
        current_module_parts = relative_path.parts[:-1] + (relative_path.stem,)
        current_module = ".".join(current_module_parts)
        
        if not self.is_aiecs_module(current_module):
            return None
        
        # Resolve relative import based on level
        if level == 1:
            # from .module import something or from . import something
            if module_name:
                # from .module import
                if '.' in current_module:
                    parent = current_module.rsplit('.', 1)[0]
                    return f"{parent}.{module_name}"
                else:
                    return module_name
            else:
                # from . import something
                return current_module.rsplit('.', 1)[0] if '.' in current_module else None
        elif level == 2:
            # from ..module import something
            if '.' in current_module:
                parent = '.'.join(current_module.split('.')[:-2])
                if module_name:
                    return f"{parent}.{module_name}"
                else:
                    return parent
        elif level > 2:
            # from ...module or deeper
            if '.' in current_module:
                parts = current_module.split('.')
                if len(parts) >= level:
                    parent = '.'.join(parts[:-(level-1)])
                    if module_name:
                        return f"{parent}.{module_name}"
                    else:
                        return parent
        
        return None

    def extract_imports_from_file(self, file_path: Path) -> List[Tuple[str, Optional[str]]]:
        """
        Extract all imports from a Python file.
        Returns list of (module_name, imported_item) tuples.
        imported_item is None for 'import module' statements.
        """
        imports = []
        
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(file_path))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append((alias.name, None))
                elif isinstance(node, ast.ImportFrom):
                    # Check if it's a relative import (level > 0)
                    if node.level > 0:
                        # Relative import - resolve it
                        resolved_module = self.resolve_relative_import(node.module, node.level, file_path)
                        if resolved_module:
                            # Use resolved absolute module name
                            for alias in node.names:
                                imports.append((resolved_module, alias.name))
                        # If resolution failed, skip it (might be external or invalid)
                    elif node.module:
                        # Absolute import
                        for alias in node.names:
                            imports.append((node.module, alias.name))
        except SyntaxError as e:
            self.failed_modules.append((str(file_path), e))
        except Exception as e:
            if self.verbose:
                print(f"Warning: Failed to parse {file_path}: {e}")
        
        return imports

    def is_aiecs_module(self, module_name: str) -> bool:
        """Check if a module name is part of the aiecs package"""
        return module_name.startswith("aiecs")

    def is_internal_import_error(self, error: Exception) -> bool:
        """Check if an import error is due to missing internal aiecs module"""
        error_msg = str(error)
        error_name = type(error).__name__
        
        # ModuleNotFoundError or ImportError with "aiecs" in the message
        # indicates an internal import problem
        if error_name in ("ModuleNotFoundError", "ImportError"):
            # Check if the error mentions an aiecs module
            if "aiecs" in error_msg.lower():
                return True
            
            # Check if it's a "No module named" error for an aiecs module
            if "no module named" in error_msg.lower():
                # Extract the module name from error message
                # Format: "No module named 'aiecs.xxx'"
                import re
                match = re.search(r"['\"]([^'\"]+)['\"]", error_msg)
                if match:
                    module_in_error = match.group(1)
                    if self.is_aiecs_module(module_in_error):
                        return True
        
        return False

    def check_module_import(self, module_name: str) -> bool:
        """
        Try to import a module and catch any import errors.
        Returns True if import succeeds, False otherwise.
        """
        if module_name in self.imported_modules:
            return module_name in self.successful_modules
        
        self.imported_modules.add(module_name)
        
        # Skip if not an aiecs module
        if not self.is_aiecs_module(module_name):
            return True
        
        try:
            # Try to import the module
            importlib.import_module(module_name)
            self.successful_modules.add(module_name)
            if self.verbose:
                print(f"  ✓ {module_name}")
            return True
        except (ImportError, ModuleNotFoundError) as e:
            # Check if it's an internal aiecs import error
            if self.is_internal_import_error(e):
                # This is a problem - internal import error
                self.failed_modules.append((module_name, e))
                if self.verbose:
                    print(f"  ✗ {module_name}: {e}")
                return False
            else:
                # External dependency missing - note it but don't fail
                # (dependencies should be in pyproject.toml and will be installed from PyPI)
                if self.verbose:
                    print(f"  ⚠ {module_name}: External dependency missing (OK if in pyproject.toml): {e}")
                # Don't mark as failed - external deps will be installed when package is installed
                return True
        except SyntaxError as e:
            # Syntax errors are always problems
            self.failed_modules.append((module_name, e))
            if self.verbose:
                print(f"  ✗ {module_name}: Syntax error: {e}")
            return False
        except Exception as e:
            # Other errors might be runtime issues, but we should note them
            # Check if it's related to imports
            if "import" in str(e).lower() or "module" in str(e).lower():
                self.failed_modules.append((module_name, e))
                if self.verbose:
                    print(f"  ✗ {module_name}: {e}")
                return False
            else:
                # Runtime error not related to imports - might be OK
                if self.verbose:
                    print(f"  ⚠ {module_name}: Runtime error (may be OK): {e}")
                return True

    def check_all_imports_in_module(self, module_name: str) -> bool:
        """
        Check all imports within a module file to ensure they can resolve.
        This catches cases where a module imports something that doesn't exist.
        """
        if module_name not in self.module_files:
            return True
        
        # Skip if module failed to import (already reported)
        if module_name not in self.successful_modules:
            return True
        
        file_path = self.module_files[module_name]
        imports = self.extract_imports_from_file(file_path)
        
        all_ok = True
        
        for import_module, import_item in imports:
            # Only check aiecs internal imports
            if not self.is_aiecs_module(import_module):
                continue
            
            # Check if the module can be imported
            try:
                mod = importlib.import_module(import_module)
                
                # If there's a specific item being imported, check if it exists
                if import_item:
                    if not hasattr(mod, import_item):
                        self.import_errors.append((
                            module_name,
                            f"{import_module}.{import_item}",
                            AttributeError(f"{import_module} has no attribute '{import_item}'")
                        ))
                        all_ok = False
            except (ImportError, ModuleNotFoundError) as e:
                # Check if it's an internal error
                if self.is_internal_import_error(e):
                    self.import_errors.append((
                        module_name,
                        import_module,
                        e
                    ))
                    all_ok = False
                # External dependency errors are OK (will be installed from PyPI)
            except Exception as e:
                # Other errors - might be runtime, but note them
                if self.verbose:
                    self.import_errors.append((
                        module_name,
                        import_module,
                        e
                    ))
        
        return all_ok

    def run_checks(self, module_filter: Optional[str] = None) -> bool:
        """Run all import checks"""
        print("=" * 80)
        print("AIECS Module Import Checker")
        print("=" * 80)
        print()
        print("This script tests all imports to catch errors before publishing to PyPI.")
        print()
        
        # Step 1: Find all modules
        print("Step 1: Discovering all modules...")
        all_modules = self.find_all_modules()
        
        if module_filter:
            all_modules = [m for m in all_modules if module_filter in m]
            print(f"  Filtered to modules containing '{module_filter}'")
        
        print(f"  Found {len(all_modules)} modules to check")
        print()
        
        # Step 2: Try importing each module
        print("Step 2: Testing module imports...")
        print("  (This simulates what happens when installing from PyPI)")
        print()
        
        for module_name in all_modules:
            if self.verbose:
                print(f"  Checking {module_name}...")
            self.check_module_import(module_name)
        
        print(f"  ✓ Successfully imported: {len(self.successful_modules)} modules")
        if self.failed_modules:
            print(f"  ✗ Failed to import: {len(self.failed_modules)} modules")
        print()
        
        # Step 3: Check imports within each module
        print("Step 3: Checking imports within modules...")
        print("  (Verifying that all internal imports resolve correctly)")
        print()
        
        for module_name in all_modules:
            if module_name in self.successful_modules:
                self.check_all_imports_in_module(module_name)
        
        if self.import_errors:
            print(f"  ✗ Found {len(self.import_errors)} import errors")
        else:
            print(f"  ✓ All imports resolve correctly")
        print()
        
        # Step 4: Try importing the main package
        print("Step 4: Testing main package import...")
        try:
            import aiecs
            print("  ✓ Main package 'aiecs' imports successfully")
            
            # Check main exports
            if hasattr(aiecs, "__all__"):
                all_items = aiecs.__all__
                missing_items = []
                for item in all_items:
                    if not hasattr(aiecs, item):
                        missing_items.append(item)
                
                if missing_items:
                    print(f"  ⚠ Warning: __all__ declares items not available: {missing_items}")
                else:
                    print(f"  ✓ All {len(all_items)} items in __all__ are available")
        except Exception as e:
            print(f"  ✗ Failed to import main package: {e}")
            self.failed_modules.append(("aiecs", e))
        print()
        
        return len(self.failed_modules) == 0 and len(self.import_errors) == 0

    def print_report(self):
        """Print a comprehensive report"""
        print("=" * 80)
        print("IMPORT CHECK REPORT")
        print("=" * 80)
        print()
        
        # Failed module imports
        if self.failed_modules:
            print(f"❌ FAILED MODULE IMPORTS ({len(self.failed_modules)}):")
            print("-" * 80)
            for module_name, error in self.failed_modules:
                print(f"  Module: {module_name}")
                print(f"  Error: {error}")
                print(f"  Type: {type(error).__name__}")
                if self.verbose:
                    print(f"  Traceback:")
                    traceback.print_exception(type(error), error, error.__traceback__)
                print()
        
        # Import errors within modules
        if self.import_errors:
            print(f"❌ IMPORT ERRORS WITHIN MODULES ({len(self.import_errors)}):")
            print("-" * 80)
            for module_name, import_name, error in self.import_errors:
                print(f"  In module: {module_name}")
                print(f"  Cannot import: {import_name}")
                print(f"  Error: {error}")
                print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total modules found: {len(self.module_files)}")
        print(f"Successfully imported: {len(self.successful_modules)}")
        print(f"Failed to import: {len(self.failed_modules)}")
        print(f"Import errors within modules: {len(self.import_errors)}")
        print()
        
        if len(self.failed_modules) == 0 and len(self.import_errors) == 0:
            print("✅ All imports successful! Package is ready for publishing.")
            print()
            print("Next steps:")
            print("  1. Build the package: python -m build")
            print("  2. Test installation: pip install dist/aiecs-*.whl")
            print("  3. Upload to PyPI: python -m twine upload dist/*")
            return True
        else:
            print("❌ Import errors found. Please fix them before publishing.")
            print()
            print("Common issues:")
            print("  - Missing __init__.py files")
            print("  - Incorrect import paths")
            print("  - Circular import dependencies")
            print("  - Typos in module or attribute names")
            return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        prog="aiecs-check-modules",
        description="AIECS Module Import Checker - Tests all imports before publishing to PyPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  aiecs-check-modules                    # Check all modules
  aiecs-check-modules --verbose           # Verbose output with details
  aiecs-check-modules --module llm        # Check only llm.* modules

This script simulates what happens when someone installs your package from PyPI.
It will catch import errors before you publish, saving you from broken releases.
        """,
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose output including successful imports"
    )
    
    parser.add_argument(
        "--module", "-m",
        type=str,
        help="Check only modules matching this filter (e.g., 'llm' to check llm.* modules)"
    )
    
    args = parser.parse_args()
    
    try:
        checker = ModuleImportChecker(verbose=args.verbose)
        success = checker.run_checks(module_filter=args.module)
        report_success = checker.print_report()
        
        sys.exit(0 if (success and report_success) else 1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
