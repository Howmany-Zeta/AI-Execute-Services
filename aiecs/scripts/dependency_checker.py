#!/usr/bin/env python3
"""
Comprehensive dependency checker for AIECS tools.

This script checks all system dependencies, Python packages, and model files
required by various AIECS tools and provides detailed status reports and
installation instructions.
"""

import os
import sys
import subprocess
import platform
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum


class DependencyStatus(Enum):
    """Status of a dependency check."""
    AVAILABLE = "available"
    MISSING = "missing"
    PARTIAL = "partial"
    ERROR = "error"


@dataclass
class DependencyInfo:
    """Information about a dependency."""
    name: str
    status: DependencyStatus
    description: str
    install_command: Optional[str] = None
    install_url: Optional[str] = None
    impact: str = ""
    is_critical: bool = True


@dataclass
class ToolDependencies:
    """Dependencies for a specific tool."""
    tool_name: str
    system_deps: List[DependencyInfo]
    python_deps: List[DependencyInfo]
    model_deps: List[DependencyInfo]
    optional_deps: List[DependencyInfo]


class DependencyChecker:
    """Main dependency checker class."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.system = platform.system().lower()
        self.architecture = platform.machine().lower()
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('dependency_check.log')
            ]
        )
        return logging.getLogger(__name__)
    
    def check_system_command(self, command: str, version_flag: str = "--version") -> DependencyStatus:
        """Check if a system command is available."""
        try:
            result = subprocess.run(
                [command, version_flag],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return DependencyStatus.AVAILABLE
            else:
                return DependencyStatus.MISSING
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            return DependencyStatus.MISSING
    
    def check_python_package(self, package_name: str) -> DependencyStatus:
        """Check if a Python package is installed."""
        try:
            __import__(package_name)
            return DependencyStatus.AVAILABLE
        except ImportError:
            return DependencyStatus.MISSING
    
    def check_file_exists(self, file_path: str) -> DependencyStatus:
        """Check if a file exists."""
        if os.path.exists(file_path):
            return DependencyStatus.AVAILABLE
        else:
            return DependencyStatus.MISSING
    
    def check_directory_exists(self, dir_path: str) -> DependencyStatus:
        """Check if a directory exists."""
        if os.path.isdir(dir_path):
            return DependencyStatus.AVAILABLE
        else:
            return DependencyStatus.MISSING
    
    def get_system_package_manager(self) -> str:
        """Get the appropriate package manager for the system."""
        if self.system == "linux":
            if shutil.which("apt-get"):
                return "apt-get"
            elif shutil.which("yum"):
                return "yum"
            elif shutil.which("dnf"):
                return "dnf"
            elif shutil.which("pacman"):
                return "pacman"
        elif self.system == "darwin":
            if shutil.which("brew"):
                return "brew"
        elif self.system == "windows":
            return "chocolatey"
        return "unknown"
    
    def check_image_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Image Tool."""
        system_deps = []
        python_deps = []
        model_deps = []
        optional_deps = []
        
        # Tesseract OCR
        tesseract_status = self.check_system_command("tesseract")
        system_deps.append(DependencyInfo(
            name="Tesseract OCR",
            status=tesseract_status,
            description="OCR engine for text extraction from images",
            install_command=self._get_tesseract_install_command(),
            impact="OCR functionality will be unavailable",
            is_critical=True
        ))
        
        # Pillow system dependencies
        pillow_status = self._check_pillow_system_deps()
        system_deps.append(DependencyInfo(
            name="Pillow System Libraries",
            status=pillow_status,
            description="Image processing system libraries (libjpeg, libpng, etc.)",
            install_command=self._get_pillow_system_deps_command(),
            impact="Image processing may fail or be limited",
            is_critical=True
        ))
        
        # Python packages
        python_packages = ["PIL", "pytesseract"]
        for pkg in python_packages:
            status = self.check_python_package(pkg)
            python_deps.append(DependencyInfo(
                name=pkg,
                status=status,
                description=f"Python package: {pkg}",
                install_command=f"pip install {pkg}",
                impact=f"{pkg} functionality will be unavailable",
                is_critical=True
            ))
        
        # Tesseract language packs
        lang_packs = ["eng", "chi_sim", "chi_tra", "fra", "deu", "jpn", "kor", "rus", "spa"]
        for lang in lang_packs:
            status = self._check_tesseract_lang_pack(lang)
            model_deps.append(DependencyInfo(
                name=f"Tesseract {lang}",
                status=status,
                description=f"Tesseract language pack for {lang}",
                install_command=self._get_tesseract_lang_install_command(lang),
                impact=f"OCR in {lang} language will be unavailable",
                is_critical=False
            ))
        
        return ToolDependencies(
            tool_name="Image Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps
        )
    
    def check_classfire_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for ClassFire Tool."""
        system_deps = []
        python_deps = []
        model_deps = []
        optional_deps = []
        
        # Python packages
        python_packages = ["spacy", "transformers", "nltk", "rake_nltk", "spacy_pkuseg"]
        for pkg in python_packages:
            status = self.check_python_package(pkg)
            is_critical = pkg != "spacy_pkuseg"  # spacy_pkuseg is optional
            python_deps.append(DependencyInfo(
                name=pkg,
                status=status,
                description=f"Python package: {pkg}",
                install_command=f"pip install {pkg}",
                impact=f"{pkg} functionality will be unavailable",
                is_critical=is_critical
            ))
        
        # spaCy models
        spacy_models = ["en_core_web_sm", "zh_core_web_sm"]
        for model in spacy_models:
            status = self._check_spacy_model(model)
            is_critical = model == "en_core_web_sm"  # Only English model is critical
            model_deps.append(DependencyInfo(
                name=f"spaCy {model}",
                status=status,
                description=f"spaCy model: {model}",
                install_command=f"python -m spacy download {model}",
                impact=f"Text processing in {model.split('_')[0]} language will be unavailable",
                is_critical=is_critical
            ))

        # spaCy PKUSeg model (optional Chinese segmentation)
        pkuseg_status = self._check_spacy_pkuseg_model()
        model_deps.append(DependencyInfo(
            name="spaCy PKUSeg",
            status=pkuseg_status,
            description="Chinese text segmentation model for spaCy",
            install_command="pip install spacy_pkuseg",
            impact="Advanced Chinese text segmentation will be unavailable",
            is_critical=False
        ))
        
        # Transformers models
        transformers_models = ["facebook/bart-large-cnn", "t5-base"]
        for model in transformers_models:
            status = self._check_transformers_model(model)
            model_deps.append(DependencyInfo(
                name=f"Transformers {model}",
                status=status,
                description=f"Transformers model: {model}",
                install_command="Models download automatically on first use",
                impact=f"Text summarization with {model} will be unavailable",
                is_critical=False
            ))
        
        # NLTK data
        nltk_data = ["stopwords", "punkt", "wordnet", "averaged_perceptron_tagger"]
        for data in nltk_data:
            status = self._check_nltk_data(data)
            model_deps.append(DependencyInfo(
                name=f"NLTK {data}",
                status=status,
                description=f"NLTK data: {data}",
                install_command=f"python -c \"import nltk; nltk.download('{data}')\"",
                impact=f"NLTK {data} functionality will be unavailable",
                is_critical=True
            ))
        
        return ToolDependencies(
            tool_name="ClassFire Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps
        )
    
    def check_office_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Office Tool."""
        system_deps = []
        python_deps = []
        model_deps = []
        optional_deps = []
        
        # Java Runtime Environment
        java_status = self.check_system_command("java", "-version")
        system_deps.append(DependencyInfo(
            name="Java Runtime Environment",
            status=java_status,
            description="Java runtime for Apache Tika document parsing",
            install_command=self._get_java_install_command(),
            impact="Document parsing with Tika will be unavailable",
            is_critical=True
        ))
        
        # Tesseract OCR
        tesseract_status = self.check_system_command("tesseract")
        system_deps.append(DependencyInfo(
            name="Tesseract OCR",
            status=tesseract_status,
            description="OCR engine for image text extraction",
            install_command=self._get_tesseract_install_command(),
            impact="OCR functionality will be unavailable",
            is_critical=False
        ))
        
        # Python packages (package_name: import_name)
        python_packages = {
            "tika": "tika",
            "python-docx": "docx",  # Package name vs import name
            "python-pptx": "pptx",  # Package name vs import name
            "openpyxl": "openpyxl",
            "pdfplumber": "pdfplumber",
            "pytesseract": "pytesseract",
            "PIL": "PIL"
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(DependencyInfo(
                name=pkg_name,
                status=status,
                description=f"Python package: {pkg_name}",
                install_command=f"pip install {pkg_name}",
                impact=f"{pkg_name} functionality will be unavailable",
                is_critical=True
            ))
        
        return ToolDependencies(
            tool_name="Office Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps
        )
    
    def check_stats_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Stats Tool."""
        system_deps = []
        python_deps = []
        model_deps = []
        optional_deps = []
        
        # pyreadstat system dependencies
        pyreadstat_status = self._check_pyreadstat_system_deps()
        system_deps.append(DependencyInfo(
            name="libreadstat",
            status=pyreadstat_status,
            description="System library for reading SAS, SPSS, Stata files",
            install_command=self._get_pyreadstat_install_command(),
            impact="SAS, SPSS, Stata file reading will be unavailable",
            is_critical=False
        ))
        
        # Excel system dependencies
        excel_status = self._check_excel_system_deps()
        system_deps.append(DependencyInfo(
            name="Excel System Libraries",
            status=excel_status,
            description="System libraries for Excel file processing",
            install_command=self._get_excel_system_deps_command(),
            impact="Excel file processing may be limited",
            is_critical=False
        ))
        
        # Python packages (package_name: import_name)
        python_packages = {
            "pandas": "pandas",
            "numpy": "numpy",
            "scipy": "scipy",
            "scikit-learn": "sklearn",  # Package name vs import name
            "statsmodels": "statsmodels",
            "pyreadstat": "pyreadstat",
            "openpyxl": "openpyxl"
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(DependencyInfo(
                name=pkg_name,
                status=status,
                description=f"Python package: {pkg_name}",
                install_command=f"pip install {pkg_name}",
                impact=f"{pkg_name} functionality will be unavailable",
                is_critical=True
            ))
        
        return ToolDependencies(
            tool_name="Stats Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps
        )
    
    def check_report_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Report Tool."""
        system_deps = []
        python_deps = []
        model_deps = []
        optional_deps = []
        
        # WeasyPrint system dependencies
        weasyprint_status = self._check_weasyprint_system_deps()
        system_deps.append(DependencyInfo(
            name="WeasyPrint System Libraries",
            status=weasyprint_status,
            description="System libraries for PDF generation (cairo, pango, etc.)",
            install_command=self._get_weasyprint_install_command(),
            impact="PDF generation will be unavailable",
            is_critical=False
        ))
        
        # Matplotlib system dependencies
        matplotlib_status = self._check_matplotlib_system_deps()
        system_deps.append(DependencyInfo(
            name="Matplotlib System Libraries",
            status=matplotlib_status,
            description="System libraries for chart generation",
            install_command=self._get_matplotlib_system_deps_command(),
            impact="Chart generation may be limited",
            is_critical=False
        ))
        
        # Python packages (package_name: import_name)
        python_packages = {
            "jinja2": "jinja2",
            "matplotlib": "matplotlib",
            "weasyprint": "weasyprint",
            "bleach": "bleach",
            "markdown": "markdown",
            "pandas": "pandas",
            "openpyxl": "openpyxl",
            "python-docx": "docx",  # Package name vs import name
            "python-pptx": "pptx"   # Package name vs import name
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(DependencyInfo(
                name=pkg_name,
                status=status,
                description=f"Python package: {pkg_name}",
                install_command=f"pip install {pkg_name}",
                impact=f"{pkg_name} functionality will be unavailable",
                is_critical=True
            ))
        
        return ToolDependencies(
            tool_name="Report Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps
        )
    
    def check_scraper_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Scraper Tool."""
        system_deps = []
        python_deps = []
        model_deps = []
        optional_deps = []
        
        # Playwright browsers
        playwright_status = self._check_playwright_browsers()
        system_deps.append(DependencyInfo(
            name="Playwright Browsers",
            status=playwright_status,
            description="Browser binaries for JavaScript rendering",
            install_command="playwright install",
            impact="JavaScript rendering will be unavailable",
            is_critical=False
        ))
        
        # Playwright system dependencies
        playwright_deps_status = self._check_playwright_system_deps()
        system_deps.append(DependencyInfo(
            name="Playwright System Dependencies",
            status=playwright_deps_status,
            description="System libraries for browser automation",
            install_command="playwright install-deps",
            impact="Browser automation may fail",
            is_critical=False
        ))
        
        # Python packages (package_name: import_name)
        python_packages = {
            "playwright": "playwright",
            "scrapy": "scrapy",
            "httpx": "httpx",
            "beautifulsoup4": "bs4",  # Package name vs import name
            "lxml": "lxml"
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(DependencyInfo(
                name=pkg_name,
                status=status,
                description=f"Python package: {pkg_name}",
                install_command=f"pip install {pkg_name}",
                impact=f"{pkg_name} functionality will be unavailable",
                is_critical=True
            ))
        
        return ToolDependencies(
            tool_name="Scraper Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps
        )
    
    def _check_pillow_system_deps(self) -> DependencyStatus:
        """Check Pillow system dependencies."""
        try:
            from PIL import Image
            # Try to create a simple image to test system libraries
            img = Image.new('RGB', (10, 10), color='red')
            img.save('/tmp/test_pillow.png')
            os.remove('/tmp/test_pillow.png')
            return DependencyStatus.AVAILABLE
        except Exception:
            return DependencyStatus.MISSING
    
    def _check_tesseract_lang_pack(self, lang: str) -> DependencyStatus:
        """Check if a Tesseract language pack is installed."""
        try:
            result = subprocess.run(
                ["tesseract", "--list-langs"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0 and lang in result.stdout:
                return DependencyStatus.AVAILABLE
            else:
                return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.MISSING
    
    def _check_spacy_model(self, model: str) -> DependencyStatus:
        """Check if a spaCy model is installed."""
        try:
            import spacy
            spacy.load(model)
            return DependencyStatus.AVAILABLE
        except OSError:
            return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.ERROR
    
    def _check_transformers_model(self, model: str) -> DependencyStatus:
        """Check if a Transformers model is available."""
        try:
            from transformers import pipeline
            # Try to load the model (this will download if not present)
            pipe = pipeline("summarization", model=model)
            return DependencyStatus.AVAILABLE
        except Exception:
            return DependencyStatus.MISSING
    
    def _check_nltk_data(self, data: str) -> DependencyStatus:
        """Check if NLTK data is available."""
        try:
            import nltk
            nltk.data.find(f'corpora/{data}')
            return DependencyStatus.AVAILABLE
        except LookupError:
            return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.ERROR

    def _check_spacy_pkuseg_model(self) -> DependencyStatus:
        """Check if spaCy PKUSeg model is available."""
        try:
            import spacy_pkuseg
            # Test basic functionality
            seg = spacy_pkuseg.pkuseg()
            test_result = list(seg.cut("测试"))
            return DependencyStatus.AVAILABLE
        except ImportError:
            return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.ERROR
    
    def _check_pyreadstat_system_deps(self) -> DependencyStatus:
        """Check pyreadstat system dependencies."""
        try:
            import pyreadstat
            return DependencyStatus.AVAILABLE
        except ImportError:
            return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.ERROR
    
    def _check_excel_system_deps(self) -> DependencyStatus:
        """Check Excel system dependencies."""
        try:
            import openpyxl
            return DependencyStatus.AVAILABLE
        except ImportError:
            return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.ERROR
    
    def _check_weasyprint_system_deps(self) -> DependencyStatus:
        """Check WeasyPrint system dependencies."""
        try:
            import weasyprint
            return DependencyStatus.AVAILABLE
        except ImportError:
            return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.ERROR
    
    def _check_matplotlib_system_deps(self) -> DependencyStatus:
        """Check Matplotlib system dependencies."""
        try:
            import matplotlib.pyplot as plt
            plt.figure()
            return DependencyStatus.AVAILABLE
        except Exception:
            return DependencyStatus.MISSING
    
    def _check_playwright_browsers(self) -> DependencyStatus:
        """Check if Playwright browsers are installed."""
        browsers_dir = Path.home() / ".cache" / "ms-playwright"
        if browsers_dir.exists() and any(browsers_dir.iterdir()):
            return DependencyStatus.AVAILABLE
        else:
            return DependencyStatus.MISSING
    
    def _check_playwright_system_deps(self) -> DependencyStatus:
        """Check Playwright system dependencies."""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                browser.close()
            return DependencyStatus.AVAILABLE
        except Exception:
            return DependencyStatus.MISSING
    
    def _get_tesseract_install_command(self) -> str:
        """Get Tesseract installation command for current system."""
        if self.system == "linux":
            return "sudo apt-get install tesseract-ocr tesseract-ocr-eng"
        elif self.system == "darwin":
            return "brew install tesseract"
        elif self.system == "windows":
            return "choco install tesseract"
        return "Please install Tesseract OCR manually"
    
    def _get_pillow_system_deps_command(self) -> str:
        """Get Pillow system dependencies installation command."""
        if self.system == "linux":
            return "sudo apt-get install libjpeg-dev zlib1g-dev libpng-dev libtiff-dev libwebp-dev libopenjp2-7-dev"
        elif self.system == "darwin":
            return "brew install libjpeg zlib libpng libtiff webp openjpeg"
        return "Please install image processing libraries manually"
    
    def _get_tesseract_lang_install_command(self, lang: str) -> str:
        """Get Tesseract language pack installation command."""
        if self.system == "linux":
            return f"sudo apt-get install tesseract-ocr-{lang}"
        elif self.system == "darwin":
            return f"brew install tesseract-lang-{lang}"
        return f"Please install Tesseract {lang} language pack manually"
    
    def _get_java_install_command(self) -> str:
        """Get Java installation command."""
        if self.system == "linux":
            return "sudo apt-get install openjdk-11-jdk"
        elif self.system == "darwin":
            return "brew install openjdk@11"
        elif self.system == "windows":
            return "choco install openjdk11"
        return "Please install Java 11 or later manually"
    
    def _get_pyreadstat_install_command(self) -> str:
        """Get pyreadstat installation command."""
        if self.system == "linux":
            return "sudo apt-get install libreadstat-dev && pip install pyreadstat"
        elif self.system == "darwin":
            return "brew install readstat && pip install pyreadstat"
        return "Please install libreadstat and pyreadstat manually"
    
    def _get_excel_system_deps_command(self) -> str:
        """Get Excel system dependencies installation command."""
        if self.system == "linux":
            return "sudo apt-get install libxml2-dev libxslt1-dev"
        elif self.system == "darwin":
            return "brew install libxml2 libxslt"
        return "Please install XML processing libraries manually"
    
    def _get_weasyprint_install_command(self) -> str:
        """Get WeasyPrint installation command."""
        if self.system == "linux":
            return "sudo apt-get install libcairo2-dev libpango1.0-dev libgdk-pixbuf2.0-dev libffi-dev shared-mime-info"
        elif self.system == "darwin":
            return "brew install cairo pango gdk-pixbuf libffi"
        return "Please install WeasyPrint dependencies manually"
    
    def _get_matplotlib_system_deps_command(self) -> str:
        """Get Matplotlib system dependencies installation command."""
        if self.system == "linux":
            return "sudo apt-get install libfreetype6-dev libpng-dev libjpeg-dev libtiff-dev libwebp-dev"
        elif self.system == "darwin":
            return "brew install freetype libpng libjpeg libtiff webp"
        return "Please install image processing libraries manually"
    
    def check_all_dependencies(self) -> Dict[str, ToolDependencies]:
        """Check all tool dependencies."""
        self.logger.info("Starting comprehensive dependency check...")
        
        tools = {
            "image": self.check_image_tool_dependencies(),
            "classfire": self.check_classfire_tool_dependencies(),
            "office": self.check_office_tool_dependencies(),
            "stats": self.check_stats_tool_dependencies(),
            "report": self.check_report_tool_dependencies(),
            "scraper": self.check_scraper_tool_dependencies(),
        }
        
        return tools
    
    def generate_report(self, tools: Dict[str, ToolDependencies]) -> str:
        """Generate a comprehensive dependency report."""
        report = []
        report.append("=" * 80)
        report.append("AIECS DEPENDENCY CHECK REPORT")
        report.append("=" * 80)
        report.append(f"System: {self.system.title()} {self.architecture}")
        report.append(f"Python: {self.python_version}")
        report.append(f"Package Manager: {self.get_system_package_manager()}")
        report.append("")
        
        total_issues = 0
        critical_issues = 0
        
        for tool_name, tool_deps in tools.items():
            report.append(f"🔧 {tool_deps.tool_name.upper()}")
            report.append("-" * 40)
            
            # System dependencies
            if tool_deps.system_deps:
                report.append("📦 System Dependencies:")
                for dep in tool_deps.system_deps:
                    status_icon = "✅" if dep.status == DependencyStatus.AVAILABLE else "❌" if dep.is_critical else "⚠️"
                    report.append(f"  {status_icon} {dep.name}: {dep.status.value}")
                    if dep.status != DependencyStatus.AVAILABLE:
                        total_issues += 1
                        if dep.is_critical:
                            critical_issues += 1
                        if dep.install_command:
                            report.append(f"     Install: {dep.install_command}")
                        if dep.impact:
                            report.append(f"     Impact: {dep.impact}")
                report.append("")
            
            # Python dependencies
            if tool_deps.python_deps:
                report.append("🐍 Python Dependencies:")
                for dep in tool_deps.python_deps:
                    status_icon = "✅" if dep.status == DependencyStatus.AVAILABLE else "❌"
                    report.append(f"  {status_icon} {dep.name}: {dep.status.value}")
                    if dep.status != DependencyStatus.AVAILABLE:
                        total_issues += 1
                        critical_issues += 1
                        if dep.install_command:
                            report.append(f"     Install: {dep.install_command}")
                        if dep.impact:
                            report.append(f"     Impact: {dep.impact}")
                report.append("")
            
            # Model dependencies
            if tool_deps.model_deps:
                report.append("🤖 Model Dependencies:")
                for dep in tool_deps.model_deps:
                    status_icon = "✅" if dep.status == DependencyStatus.AVAILABLE else "❌" if dep.is_critical else "⚠️"
                    report.append(f"  {status_icon} {dep.name}: {dep.status.value}")
                    if dep.status != DependencyStatus.AVAILABLE:
                        total_issues += 1
                        if dep.is_critical:
                            critical_issues += 1
                        if dep.install_command:
                            report.append(f"     Install: {dep.install_command}")
                        if dep.impact:
                            report.append(f"     Impact: {dep.impact}")
                report.append("")
            
            # Optional dependencies
            if tool_deps.optional_deps:
                report.append("🔧 Optional Dependencies:")
                for dep in tool_deps.optional_deps:
                    status_icon = "✅" if dep.status == DependencyStatus.AVAILABLE else "⚠️"
                    report.append(f"  {status_icon} {dep.name}: {dep.status.value}")
                    if dep.status != DependencyStatus.AVAILABLE and dep.install_command:
                        report.append(f"     Install: {dep.install_command}")
                report.append("")
        
        # Summary
        report.append("=" * 80)
        report.append("SUMMARY")
        report.append("=" * 80)
        report.append(f"Total Issues: {total_issues}")
        report.append(f"Critical Issues: {critical_issues}")
        report.append(f"Optional Issues: {total_issues - critical_issues}")
        
        if critical_issues == 0:
            report.append("")
            report.append("🎉 All critical dependencies are available!")
            report.append("AIECS is ready to use with full functionality.")
        else:
            report.append("")
            report.append("⚠️  Some critical dependencies are missing.")
            report.append("Please install the missing dependencies to enable full functionality.")
        
        return "\n".join(report)
    
    def save_report(self, report: str, filename: str = "dependency_report.txt"):
        """Save the report to a file."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report)
        self.logger.info(f"Report saved to {filename}")


def main():
    """Main function."""
    checker = DependencyChecker()
    
    print("🔍 Checking AIECS dependencies...")
    print("This may take a few minutes for model checks...")
    print()
    
    # Check all dependencies
    tools = checker.check_all_dependencies()
    
    # Generate and display report
    report = checker.generate_report(tools)
    print(report)
    
    # Save report
    checker.save_report(report)
    
    # Return exit code based on critical issues
    critical_issues = sum(
        1 for tool_deps in tools.values()
        for dep in tool_deps.system_deps + tool_deps.python_deps + tool_deps.model_deps
        if dep.status != DependencyStatus.AVAILABLE and dep.is_critical
    )
    
    if critical_issues == 0:
        print("\n✅ All critical dependencies are available!")
        return 0
    else:
        print(f"\n❌ {critical_issues} critical dependencies are missing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())





