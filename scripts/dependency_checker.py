#!/usr/bin/env python3
"""
Python Middleware Global Dependency Checker

This script analyzes all Python files in the python-middleware project to:
1. Identify all imported packages and modules
2. Categorize them as runtime vs development dependencies
3. Compare against current pyproject.toml
4. Report missing dependencies
"""

import ast
import os
import sys
import re
from pathlib import Path
from typing import Set, Dict, List, Tuple
try:
    import tomllib
except ImportError:
    # Fallback for Python < 3.11
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None
from collections import defaultdict

class DependencyAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.app_root = self.project_root / "app"
        self.pyproject_path = self.project_root / "pyproject.toml"

        # Standard library modules (Python 3.10+)
        self.stdlib_modules = {
            'abc', 'argparse', 'ast', 'asyncio', 'base64', 'collections', 'concurrent',
            'copy', 'datetime', 'decimal', 'enum', 'functools', 'hashlib', 'http',
            'io', 'itertools', 'json', 'logging', 'math', 'multiprocessing', 'os',
            'pathlib', 'pickle', 'platform', 'queue', 'random', 're', 'shutil',
            'socket', 'sqlite3', 'ssl', 'string', 'subprocess', 'sys', 'tempfile',
            'threading', 'time', 'typing', 'urllib', 'uuid', 'warnings', 'weakref',
            'xml', 'zipfile', 'zlib', '__future__', 'dataclasses', 'contextlib',
            'operator', 'heapq', 'bisect', 'array', 'struct', 'codecs', 'locale',
            'calendar', 'email', 'mimetypes', 'textwrap', 'unicodedata', 'html',
            'csv', 'configparser', 'fileinput', 'glob', 'fnmatch', 'linecache',
            'tempfile', 'gzip', 'bz2', 'lzma', 'tarfile', 'zipfile', 'inspect',
            'importlib', 'pkgutil', 'types', 'traceback', 'pprint'
        }

        # Development-only patterns (files that are only used in development/testing)
        self.dev_patterns = {
            'test_', '_test', 'tests/', '/test/', 'conftest', 'pytest',
            'benchmark', 'example', 'demo', 'script'
        }

        # Known package mappings (import name -> package name)
        self.package_mappings = {
            'PIL': 'pillow',
            'yaml': 'pyyaml',
            'sklearn': 'scikit-learn',
            'google.cloud': 'google-cloud-aiplatform',
            'google.auth': 'google-auth',
            'openai': 'openai',
            'anthropic': 'anthropic',
            'fastapi': 'fastapi',
            'uvicorn': 'uvicorn',
            'pydantic': 'pydantic',
            'pydantic_settings': 'pydantic-settings',
            'requests': 'requests',
            'pandas': 'pandas',
            'numpy': 'numpy',
            'matplotlib': 'matplotlib',
            'seaborn': 'seaborn',
            'plotly': 'plotly',
            'streamlit': 'streamlit',
            'celery': 'celery',
            'redis': 'redis',
            'sqlalchemy': 'sqlalchemy',
            'alembic': 'alembic',
            'psycopg2': 'psycopg2-binary',
            'asyncpg': 'asyncpg',
            'pymongo': 'pymongo',
            'elasticsearch': 'elasticsearch',
            'neo4j': 'neo4j',
            'transformers': 'transformers',
            'torch': 'torch',
            'tensorflow': 'tensorflow',
            'langchain': 'langchain',
            'chromadb': 'chromadb',
            'pinecone': 'pinecone-client',
            'weaviate': 'weaviate-client',
            'sentence_transformers': 'sentence-transformers',
            'tiktoken': 'tiktoken',
            'beautifulsoup4': 'beautifulsoup4',
            'bs4': 'beautifulsoup4',
            'lxml': 'lxml',
            'scrapy': 'scrapy',
            'selenium': 'selenium',
            'playwright': 'playwright',
            'httpx': 'httpx',
            'aiohttp': 'aiohttp',
            'websockets': 'websockets',
            'socketio': 'python-socketio',
            'engineio': 'python-engineio',
            'jwt': 'pyjwt',
            'cryptography': 'cryptography',
            'bcrypt': 'bcrypt',
            'passlib': 'passlib',
            'python_multipart': 'python-multipart',
            'jinja2': 'jinja2',
            'click': 'click',
            'typer': 'typer',
            'rich': 'rich',
            'tqdm': 'tqdm',
            'pytest': 'pytest',
            'pytest_asyncio': 'pytest-asyncio',
            'pytest_mock': 'pytest-mock',
            'black': 'black',
            'flake8': 'flake8',
            'mypy': 'mypy',
            'isort': 'isort',
            'pre_commit': 'pre-commit',
            'sphinx': 'sphinx',
            'mkdocs': 'mkdocs',
            'jupyter': 'jupyter',
            'ipython': 'ipython',
            'notebook': 'notebook',
            'grpcio': 'grpcio',
            'protobuf': 'protobuf',
            'kafka': 'kafka-python',
            'pika': 'pika',
            'kombu': 'kombu',
            'docker': 'docker',
            'kubernetes': 'kubernetes',
            'boto3': 'boto3',
            'azure': 'azure',
            'vertexai': 'vertexai',
            'crewai': 'crewai',
            'spacy': 'spacy',
            'rake_nltk': 'rake-nltk',
            'scipy': 'scipy',
            'docx': 'python-docx',
            'pptx': 'python-pptx',
            'markdown': 'markdown',
            'bleach': 'bleach',
            'typing_extensions': 'typing-extensions',
            'pyreadstat': 'pyreadstat',
            'statsmodels': 'statsmodels',
            'weasyprint': 'weasyprint',
            'pdfplumber': 'pdfplumber',
            'pytesseract': 'pytesseract',
            'tika': 'tika',
            'prometheus_client': 'prometheus-client',
            'tenacity': 'tenacity',
            'cachetools': 'cachetools',
            'python_dotenv': 'python-dotenv',
            'pyhocon': 'pyhocon',
            'ollama': 'ollama',
            'qdrant_client': 'qdrant-client',
            'igraph': 'python-igraph',
            'schedule': 'schedule',
            'six': 'six',
            'shelve': 'shelve',
            'transaction': 'transaction',
            'BTrees': 'btrees',
            'ZODB': 'zodb',
            'aiolimiter': 'aiolimiter',
            'docstring_parser': 'docstring-parser',
            'networkx': 'networkx',
            'mcp': 'mcp',
            'knext': 'knext'
        }

    def extract_imports_from_file(self, file_path: Path) -> Set[str]:
        """Extract all import statements from a Python file."""
        imports = set()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the AST
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])

        except (SyntaxError, UnicodeDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not parse {file_path}: {e}")

        return imports

    def is_development_file(self, file_path: Path) -> bool:
        """Determine if a file is development-only based on its path."""
        path_str = str(file_path).lower()
        return any(pattern in path_str for pattern in self.dev_patterns)

    def get_all_python_files(self) -> List[Path]:
        """Get all Python files in the project."""
        python_files = []
        for root, dirs, files in os.walk(self.app_root):
            # Skip __pycache__ directories
            dirs[:] = [d for d in dirs if d != '__pycache__']

            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)

        return python_files

    def analyze_dependencies(self) -> Tuple[Dict[str, Set[str]], Dict[str, Set[str]]]:
        """Analyze all dependencies and categorize them."""
        runtime_deps = defaultdict(set)
        dev_deps = defaultdict(set)

        python_files = self.get_all_python_files()

        for file_path in python_files:
            imports = self.extract_imports_from_file(file_path)
            is_dev = self.is_development_file(file_path)

            for imp in imports:
                # Skip standard library modules
                if imp in self.stdlib_modules:
                    continue

                # Skip local imports (relative to project)
                if imp in ['app', 'services', 'tools', 'llm', 'api', 'tasks']:
                    continue

                if is_dev:
                    dev_deps[imp].add(str(file_path.relative_to(self.project_root)))
                else:
                    runtime_deps[imp].add(str(file_path.relative_to(self.project_root)))

        return dict(runtime_deps), dict(dev_deps)

    def load_current_dependencies(self) -> Tuple[Set[str], Set[str]]:
        """Load current dependencies from pyproject.toml."""
        current_runtime = set()
        current_dev = set()

        if not self.pyproject_path.exists():
            print(f"Warning: {self.pyproject_path} not found")
            return current_runtime, current_dev

        if tomllib is None:
            print("Warning: tomllib not available, parsing pyproject.toml manually")
            return self._parse_toml_manually()

        try:
            with open(self.pyproject_path, 'rb') as f:
                data = tomllib.load(f)

            # Extract runtime dependencies
            if 'project' in data and 'dependencies' in data['project']:
                for dep in data['project']['dependencies']:
                    # Extract package name from dependency string
                    package_name = re.split(r'[<>=!~\[\s]', dep.strip())[0].lower()
                    current_runtime.add(package_name)

            # Extract dev dependencies from poetry format
            if 'tool' in data and 'poetry' in data['tool'] and 'group' in data['tool']['poetry']:
                if 'dev' in data['tool']['poetry']['group'] and 'dependencies' in data['tool']['poetry']['group']['dev']:
                    for dep in data['tool']['poetry']['group']['dev']['dependencies']:
                        package_name = dep.lower()
                        current_dev.add(package_name)

        except Exception as e:
            print(f"Error reading pyproject.toml: {e}")

        return current_runtime, current_dev

    def _parse_toml_manually(self) -> Tuple[Set[str], Set[str]]:
        """Manually parse pyproject.toml when tomllib is not available."""
        current_runtime = set()
        current_dev = set()

        try:
            with open(self.pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple regex-based parsing for dependencies
            # Parse [project] dependencies
            project_deps_match = re.search(r'\[project\].*?dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
            if project_deps_match:
                deps_text = project_deps_match.group(1)
                for line in deps_text.split('\n'):
                    line = line.strip()
                    if line and line.startswith('"') and line.endswith('",'):
                        dep = line.strip('"",')
                        package_name = re.split(r'[<>=!~\[\s]', dep.strip())[0].lower()
                        current_runtime.add(package_name)

            # Parse [tool.poetry.group.dev.dependencies]
            dev_deps_match = re.search(r'\[tool\.poetry\.group\.dev\.dependencies\](.*?)(?=\[|\Z)', content, re.DOTALL)
            if dev_deps_match:
                deps_text = dev_deps_match.group(1)
                for line in deps_text.split('\n'):
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        package_name = line.split('=')[0].strip().lower()
                        current_dev.add(package_name)

        except Exception as e:
            print(f"Error manually parsing pyproject.toml: {e}")

        return current_runtime, current_dev

    def map_import_to_package(self, import_name: str) -> str:
        """Map import name to package name."""
        return self.package_mappings.get(import_name, import_name.lower().replace('_', '-'))

    def generate_report(self) -> str:
        """Generate comprehensive dependency report."""
        runtime_deps, dev_deps = self.analyze_dependencies()
        current_runtime, current_dev = self.load_current_dependencies()

        report = []
        report.append("=" * 80)
        report.append("PYTHON MIDDLEWARE DEPENDENCY ANALYSIS REPORT")
        report.append("=" * 80)
        report.append("")

        # Runtime Dependencies Analysis
        report.append("🔧 RUNTIME DEPENDENCIES")
        report.append("-" * 40)

        runtime_packages = {}
        for import_name, files in runtime_deps.items():
            package_name = self.map_import_to_package(import_name)
            if package_name not in runtime_packages:
                runtime_packages[package_name] = set()
            runtime_packages[package_name].update(files)

        missing_runtime = set()
        for package_name in sorted(runtime_packages.keys()):
            files = runtime_packages[package_name]
            is_missing = package_name not in current_runtime
            status = "❌ MISSING" if is_missing else "✅ PRESENT"

            if is_missing:
                missing_runtime.add(package_name)

            report.append(f"{status} {package_name}")
            for file in sorted(files):
                report.append(f"    └── {file}")
            report.append("")

        # Development Dependencies Analysis
        report.append("🛠️  DEVELOPMENT DEPENDENCIES")
        report.append("-" * 40)

        dev_packages = {}
        for import_name, files in dev_deps.items():
            package_name = self.map_import_to_package(import_name)
            if package_name not in dev_packages:
                dev_packages[package_name] = set()
            dev_packages[package_name].update(files)

        missing_dev = set()
        for package_name in sorted(dev_packages.keys()):
            files = dev_packages[package_name]
            is_missing = package_name not in current_dev
            status = "❌ MISSING" if is_missing else "✅ PRESENT"

            if is_missing:
                missing_dev.add(package_name)

            report.append(f"{status} {package_name}")
            for file in sorted(files):
                report.append(f"    └── {file}")
            report.append("")

        # Summary
        report.append("📊 SUMMARY")
        report.append("-" * 40)
        report.append(f"Total runtime dependencies found: {len(runtime_packages)}")
        report.append(f"Missing from pyproject.toml: {len(missing_runtime)}")
        report.append(f"Total dev dependencies found: {len(dev_packages)}")
        report.append(f"Missing from pyproject.toml: {len(missing_dev)}")
        report.append("")

        # Missing Dependencies for pyproject.toml
        if missing_runtime or missing_dev:
            report.append("📝 MISSING DEPENDENCIES TO ADD TO PYPROJECT.TOML")
            report.append("-" * 60)

            if missing_runtime:
                report.append("Runtime dependencies to add to [project.dependencies]:")
                for package in sorted(missing_runtime):
                    report.append(f'    "{package}",')
                report.append("")

            if missing_dev:
                report.append("Development dependencies to add to [tool.poetry.group.dev.dependencies]:")
                for package in sorted(missing_dev):
                    report.append(f'{package} = "^1.0.0"  # Update version as needed')
                report.append("")

        # Recommendations
        report.append("💡 RECOMMENDATIONS")
        report.append("-" * 40)

        # Check for potentially unused dependencies
        unused_runtime = current_runtime - set(runtime_packages.keys())
        unused_dev = current_dev - set(dev_packages.keys())

        if unused_runtime:
            report.append("Potentially unused runtime dependencies (not found in imports):")
            for package in sorted(unused_runtime):
                report.append(f"    - {package}")
            report.append("")

        if unused_dev:
            report.append("Potentially unused dev dependencies (not found in imports):")
            for package in sorted(unused_dev):
                report.append(f"    - {package}")
            report.append("")

        # Special cases and notes
        report.append("⚠️  SPECIAL NOTES")
        report.append("-" * 40)
        report.append("1. Some packages may be imported dynamically or conditionally")
        report.append("2. Version constraints should be reviewed for compatibility")
        report.append("3. Some imports may be from sub-packages of larger packages")
        report.append("4. Consider using virtual environments for dependency isolation")
        report.append("")

        return "\n".join(report)

def main():
    """Main function to run the dependency analysis."""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        # Default to current directory's python-middleware
        project_root = Path(__file__).parent.parent

    analyzer = DependencyAnalyzer(project_root)
    report = analyzer.generate_report()

    # Print to console
    print(report)

    # Save to file
    output_file = analyzer.project_root / "scripts" / "dependency_report.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 Report saved to: {output_file}")

if __name__ == "__main__":
    main()
