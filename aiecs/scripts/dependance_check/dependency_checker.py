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
from typing import Dict, List, Optional
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
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("dependency_check.log"),
            ],
        )
        return logging.getLogger(__name__)

    def check_system_command(self, command: str, version_flag: str = "--version") -> DependencyStatus:
        """Check if a system command is available."""
        try:
            result = subprocess.run(
                [command, version_flag],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return DependencyStatus.AVAILABLE
            else:
                return DependencyStatus.MISSING
        except (
            subprocess.TimeoutExpired,
            FileNotFoundError,
            subprocess.CalledProcessError,
        ):
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
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Tesseract OCR
        tesseract_status = self.check_system_command("tesseract")
        system_deps.append(
            DependencyInfo(
                name="Tesseract OCR",
                status=tesseract_status,
                description="OCR engine for text extraction from images",
                install_command=self._get_tesseract_install_command(),
                impact="OCR functionality will be unavailable",
                is_critical=True,
            )
        )

        # Pillow system dependencies
        pillow_status = self._check_pillow_system_deps()
        system_deps.append(
            DependencyInfo(
                name="Pillow System Libraries",
                status=pillow_status,
                description="Image processing system libraries (libjpeg, libpng, etc.)",
                install_command=self._get_pillow_system_deps_command(),
                impact="Image processing may fail or be limited",
                is_critical=True,
            )
        )

        # Python packages
        python_packages = ["PIL", "pytesseract"]
        for pkg in python_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} functionality will be unavailable",
                    is_critical=True,
                )
            )

        # Tesseract language packs
        lang_packs = [
            "eng",
            "chi_sim",
            "chi_tra",
            "fra",
            "deu",
            "jpn",
            "kor",
            "rus",
            "spa",
        ]
        for lang in lang_packs:
            status = self._check_tesseract_lang_pack(lang)
            model_deps.append(
                DependencyInfo(
                    name=f"Tesseract {lang}",
                    status=status,
                    description=f"Tesseract language pack for {lang}",
                    install_command=self._get_tesseract_lang_install_command(lang),
                    impact=f"OCR in {lang} language will be unavailable",
                    is_critical=False,
                )
            )

        return ToolDependencies(
            tool_name="Image Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_classfire_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for ClassFire Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages (required)
        core_packages = ["spacy", "nltk", "rake_nltk"]
        for pkg in core_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} functionality will be unavailable",
                    is_critical=True,
                )
            )

        # Optional Python packages
        optional_packages = {
            "transformers": "Text summarization (BART/T5 models)",
            "torch": "Backend for transformers (PyTorch)",
            "spacy_pkuseg": "Advanced Chinese text segmentation",
        }
        for pkg, description in optional_packages.items():
            status = self.check_python_package(pkg)
            optional_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=description,
                    install_command=f"pip install {pkg}" if pkg != "torch" else "pip install torch (or pip install aiecs[summarization])",
                    impact=f"{description} will be unavailable",
                    is_critical=False,
                )
            )

        # spaCy models
        spacy_models = ["en_core_web_sm", "zh_core_web_sm"]
        for model in spacy_models:
            status = self._check_spacy_model(model)
            is_critical = model == "en_core_web_sm"  # Only English model is critical
            model_deps.append(
                DependencyInfo(
                    name=f"spaCy {model}",
                    status=status,
                    description=f"spaCy model: {model}",
                    install_command=f"python -m spacy download {model}",
                    impact=f"Text processing in {model.split('_')[0]} language will be unavailable",
                    is_critical=is_critical,
                )
            )

        # spaCy PKUSeg model (optional Chinese segmentation)
        pkuseg_status = self._check_spacy_pkuseg_model()
        model_deps.append(
            DependencyInfo(
                name="spaCy PKUSeg",
                status=pkuseg_status,
                description="Chinese text segmentation model for spaCy",
                install_command="pip install spacy_pkuseg",
                impact="Advanced Chinese text segmentation will be unavailable",
                is_critical=False,
            )
        )

        # Transformers models (optional - only if transformers is installed)
        if self.check_python_package("transformers") == DependencyStatus.AVAILABLE:
            transformers_models = ["facebook/bart-large-cnn", "t5-base"]
            for model in transformers_models:
                status = self._check_transformers_model(model)
                optional_deps.append(
                    DependencyInfo(
                        name=f"Transformers {model}",
                        status=status,
                        description=f"Transformers model for summarization: {model}",
                        install_command="Models download automatically on first use (requires transformers + torch)",
                        impact=f"Text summarization with {model} will be unavailable",
                        is_critical=False,
                    )
                )

        # NLTK data
        nltk_data = [
            "stopwords",
            "punkt",
            "wordnet",
            "averaged_perceptron_tagger",
        ]
        for data in nltk_data:
            status = self._check_nltk_data(data)
            # Recommend using the proper download script that handles environment-specific paths
            install_cmd = "aiecs-download-nlp-data --download  # Downloads to Poetry/virtual environment"
            
            model_deps.append(
                DependencyInfo(
                    name=f"NLTK {data}",
                    status=status,
                    description=f"NLTK data: {data}",
                    install_command=install_cmd,
                    impact=f"NLTK {data} functionality will be unavailable",
                    is_critical=True,
                )
            )

        return ToolDependencies(
            tool_name="ClassFire Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_office_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Office Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Java Runtime Environment
        java_status = self.check_system_command("java", "-version")
        system_deps.append(
            DependencyInfo(
                name="Java Runtime Environment",
                status=java_status,
                description="Java runtime for Apache Tika document parsing",
                install_command=self._get_java_install_command(),
                impact="Document parsing with Tika will be unavailable",
                is_critical=True,
            )
        )

        # Tesseract OCR
        tesseract_status = self.check_system_command("tesseract")
        system_deps.append(
            DependencyInfo(
                name="Tesseract OCR",
                status=tesseract_status,
                description="OCR engine for image text extraction",
                install_command=self._get_tesseract_install_command(),
                impact="OCR functionality will be unavailable",
                is_critical=False,
            )
        )

        # Python packages (package_name: import_name)
        python_packages = {
            "tika": "tika",
            "python-docx": "docx",  # Package name vs import name
            "python-pptx": "pptx",  # Package name vs import name
            "openpyxl": "openpyxl",
            "pdfplumber": "pdfplumber",
            "pytesseract": "pytesseract",
            "PIL": "PIL",
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} functionality will be unavailable",
                    is_critical=True,
                )
            )

        return ToolDependencies(
            tool_name="Office Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_stats_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Stats Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # pyreadstat system dependencies
        pyreadstat_status = self._check_pyreadstat_system_deps()
        system_deps.append(
            DependencyInfo(
                name="libreadstat",
                status=pyreadstat_status,
                description="System library for reading SAS, SPSS, Stata files",
                install_command=self._get_pyreadstat_install_command(),
                impact="SAS, SPSS, Stata file reading will be unavailable",
                is_critical=False,
            )
        )

        # Excel system dependencies
        excel_status = self._check_excel_system_deps()
        system_deps.append(
            DependencyInfo(
                name="Excel System Libraries",
                status=excel_status,
                description="System libraries for Excel file processing",
                install_command=self._get_excel_system_deps_command(),
                impact="Excel file processing may be limited",
                is_critical=False,
            )
        )

        # Python packages (package_name: import_name)
        python_packages = {
            "pandas": "pandas",
            "numpy": "numpy",
            "scipy": "scipy",
            "scikit-learn": "sklearn",  # Package name vs import name
            "statsmodels": "statsmodels",
            "pyreadstat": "pyreadstat",
            "openpyxl": "openpyxl",
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} functionality will be unavailable",
                    is_critical=True,
                )
            )

        return ToolDependencies(
            tool_name="Stats Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_report_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Report Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Matplotlib system dependencies (core - for chart generation)
        matplotlib_status = self._check_matplotlib_system_deps()
        system_deps.append(
            DependencyInfo(
                name="Matplotlib System Libraries",
                status=matplotlib_status,
                description="System libraries for chart generation",
                install_command=self._get_matplotlib_system_deps_command(),
                impact="Chart generation may be limited",
                is_critical=True,
            )
        )

        # Core Python packages (package_name: import_name)
        core_python_packages = {
            "jinja2": "jinja2",
            "matplotlib": "matplotlib",
            "bleach": "bleach",
            "markdown": "markdown",
            "pandas": "pandas",
            "openpyxl": "openpyxl",
            "python-docx": "docx",  # Package name vs import name
            "python-pptx": "pptx",  # Package name vs import name
        }
        for pkg_name, import_name in core_python_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} functionality will be unavailable",
                    is_critical=True,
                )
            )

        # Optional: WeasyPrint system dependencies (for PDF generation)
        weasyprint_status = self._check_weasyprint_system_deps()
        optional_deps.append(
            DependencyInfo(
                name="WeasyPrint System Libraries",
                status=weasyprint_status,
                description="System libraries for PDF generation (cairo, pango, etc.) - currently disabled",
                install_command=self._get_weasyprint_install_command(),
                impact="PDF generation functionality is currently disabled (will be re-enabled in future release)",
                is_critical=False,
            )
        )

        # Optional: WeasyPrint Python package (for PDF generation)
        weasyprint_pkg_status = self.check_python_package("weasyprint")
        optional_deps.append(
            DependencyInfo(
                name="weasyprint",
                status=weasyprint_pkg_status,
                description="Python package: weasyprint (HTML to PDF conversion) - currently disabled",
                install_command="pip install weasyprint",
                impact="PDF generation functionality is currently disabled (will be re-enabled in future release)",
                is_critical=False,
            )
        )

        return ToolDependencies(
            tool_name="Report Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_scraper_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Scraper Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Playwright browsers
        playwright_status = self._check_playwright_browsers()
        system_deps.append(
            DependencyInfo(
                name="Playwright Browsers",
                status=playwright_status,
                description="Browser binaries for JavaScript rendering",
                install_command="playwright install",
                impact="JavaScript rendering will be unavailable",
                is_critical=False,
            )
        )

        # Playwright system dependencies
        playwright_deps_status = self._check_playwright_system_deps()
        system_deps.append(
            DependencyInfo(
                name="Playwright System Dependencies",
                status=playwright_deps_status,
                description="System libraries for browser automation",
                install_command="playwright install-deps",
                impact="Browser automation may fail",
                is_critical=False,
            )
        )

        # Python packages (package_name: import_name)
        python_packages = {
            "playwright": "playwright",
            "scrapy": "scrapy",
            "httpx": "httpx",
            "beautifulsoup4": "bs4",  # Package name vs import name
            "lxml": "lxml",
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} functionality will be unavailable",
                    is_critical=True,
                )
            )

        return ToolDependencies(
            tool_name="Scraper Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def _check_pillow_system_deps(self) -> DependencyStatus:
        """Check Pillow system dependencies."""
        try:
            from PIL import Image

            # Try to create a simple image to test system libraries
            img = Image.new("RGB", (10, 10), color="red")
            img.save("/tmp/test_pillow.png")
            os.remove("/tmp/test_pillow.png")
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
                timeout=10,
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
            from transformers import pipeline  # type: ignore[import-not-found]

            # Try to load the model (this will download if not present)
            pipeline("summarization", model=model)  # Just checking if it loads
            return DependencyStatus.AVAILABLE
        except Exception:
            return DependencyStatus.MISSING

    def _check_nltk_data(self, data: str) -> DependencyStatus:
        """Check if NLTK data is available."""
        try:
            import nltk  # type: ignore[import-untyped]

            nltk.data.find(f"corpora/{data}")
            return DependencyStatus.AVAILABLE
        except LookupError:
            return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.ERROR

    def _check_spacy_pkuseg_model(self) -> DependencyStatus:
        """Check if spaCy PKUSeg model is available."""
        try:
            import spacy_pkuseg  # type: ignore[import-untyped]

            # Test basic functionality
            seg = spacy_pkuseg.pkuseg()
            list(seg.cut("测试"))
            return DependencyStatus.AVAILABLE
        except ImportError:
            return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.ERROR

    def _check_pyreadstat_system_deps(self) -> DependencyStatus:
        """Check pyreadstat system dependencies."""
        try:
            return DependencyStatus.AVAILABLE
        except ImportError:
            return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.ERROR

    def _check_excel_system_deps(self) -> DependencyStatus:
        """Check Excel system dependencies."""
        try:
            return DependencyStatus.AVAILABLE
        except ImportError:
            return DependencyStatus.MISSING
        except Exception:
            return DependencyStatus.ERROR

    def _check_weasyprint_system_deps(self) -> DependencyStatus:
        """Check WeasyPrint system dependencies."""
        try:
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

    def check_chart_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Chart Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Matplotlib system dependencies
        matplotlib_status = self._check_matplotlib_system_deps()
        system_deps.append(
            DependencyInfo(
                name="Matplotlib System Libraries",
                status=matplotlib_status,
                description="System libraries for chart generation",
                install_command=self._get_matplotlib_system_deps_command(),
                impact="Chart generation may be limited",
                is_critical=False,
            )
        )

        # Python packages
        python_packages = {
            "pandas": "pandas",
            "matplotlib": "matplotlib",
            "seaborn": "seaborn",
            "plotly": "plotly",
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            is_critical = pkg_name in ["pandas", "matplotlib"]
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} functionality will be unavailable",
                    is_critical=is_critical,
                )
            )

        return ToolDependencies(
            tool_name="Chart Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_pandas_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Pandas Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Python packages
        python_packages = ["pandas", "numpy"]
        for pkg in python_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} functionality will be unavailable",
                    is_critical=True,
                )
            )

        return ToolDependencies(
            tool_name="Pandas Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_document_parser_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Document Parser Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Note: Document Parser Tool depends on Office Tool, Image Tool, and Scraper Tool
        # We'll check their dependencies
        
        # Java Runtime Environment (from Office Tool)
        java_status = self.check_system_command("java", "-version")
        system_deps.append(
            DependencyInfo(
                name="Java Runtime Environment",
                status=java_status,
                description="Java runtime for Apache Tika document parsing",
                install_command=self._get_java_install_command(),
                impact="Document parsing with Tika will be unavailable",
                is_critical=True,
            )
        )

        # Tesseract OCR (from Image Tool)
        tesseract_status = self.check_system_command("tesseract")
        system_deps.append(
            DependencyInfo(
                name="Tesseract OCR",
                status=tesseract_status,
                description="OCR engine for image text extraction",
                install_command=self._get_tesseract_install_command(),
                impact="OCR functionality will be unavailable",
                is_critical=False,
            )
        )

        # Python packages
        python_packages = {
            "pdfplumber": "pdfplumber",
            "python-docx": "docx",
            "python-pptx": "pptx",
            "openpyxl": "openpyxl",
            "pytesseract": "pytesseract",
            "PIL": "PIL",
            "beautifulsoup4": "bs4",
            "lxml": "lxml",
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} functionality will be unavailable",
                    is_critical=True,
                )
            )

        return ToolDependencies(
            tool_name="Document Parser Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_data_loader_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Data Loader Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # pyreadstat system dependencies
        pyreadstat_status = self._check_pyreadstat_system_deps()
        system_deps.append(
            DependencyInfo(
                name="libreadstat",
                status=pyreadstat_status,
                description="System library for reading SAS, SPSS, Stata files",
                install_command=self._get_pyreadstat_install_command(),
                impact="SAS, SPSS, Stata file reading will be unavailable",
                is_critical=False,
            )
        )

        # Python packages
        python_packages = {
            "pandas": "pandas",
            "numpy": "numpy",
            "pyreadstat": "pyreadstat",
            "openpyxl": "openpyxl",
            "pyarrow": "pyarrow",
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            is_critical = pkg_name in ["pandas", "numpy"]
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} functionality will be unavailable",
                    is_critical=is_critical,
                )
            )

        return ToolDependencies(
            tool_name="Data Loader Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_data_visualizer_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Data Visualizer Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Matplotlib system dependencies
        matplotlib_status = self._check_matplotlib_system_deps()
        system_deps.append(
            DependencyInfo(
                name="Matplotlib System Libraries",
                status=matplotlib_status,
                description="System libraries for visualization",
                install_command=self._get_matplotlib_system_deps_command(),
                impact="Visualization may be limited",
                is_critical=False,
            )
        )

        # Python packages
        python_packages = {
            "pandas": "pandas",
            "numpy": "numpy",
            "matplotlib": "matplotlib",
            "seaborn": "seaborn",
            "plotly": "plotly",
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            is_critical = pkg_name in ["pandas", "matplotlib"]
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} functionality will be unavailable",
                    is_critical=is_critical,
                )
            )

        return ToolDependencies(
            tool_name="Data Visualizer Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_model_trainer_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Model Trainer Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Python packages
        python_packages = {
            "pandas": "pandas",
            "numpy": "numpy",
            "scikit-learn": "sklearn",
            "xgboost": "xgboost",
            "lightgbm": "lightgbm",
        }
        for pkg_name, import_name in python_packages.items():
            status = self.check_python_package(import_name)
            is_critical = pkg_name in ["pandas", "numpy", "scikit-learn"]
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} functionality will be unavailable",
                    is_critical=is_critical,
                )
            )

        return ToolDependencies(
            tool_name="Model Trainer Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_apisource_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for APISource Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages
        python_packages = ["pydantic", "httpx", "requests"]
        for pkg in python_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} functionality will be unavailable",
                    is_critical=True,
                )
            )

        # Optional: Redis for caching
        redis_status = self.check_python_package("redis")
        optional_deps.append(
            DependencyInfo(
                name="redis",
                status=redis_status,
                description="Python package: redis (Advanced caching support)",
                install_command="pip install redis",
                impact="Advanced caching features will be unavailable",
                is_critical=False,
            )
        )

        return ToolDependencies(
            tool_name="APISource Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_search_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Search Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages
        python_packages = ["pydantic", "httpx", "requests"]
        for pkg in python_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} functionality will be unavailable",
                    is_critical=True,
                )
            )

        # Optional: Redis for intelligent caching
        redis_status = self.check_python_package("redis")
        optional_deps.append(
            DependencyInfo(
                name="redis",
                status=redis_status,
                description="Python package: redis (Intelligent caching support)",
                install_command="pip install redis",
                impact="Intelligent caching features will be unavailable",
                is_critical=False,
            )
        )

        # Optional: BeautifulSoup for HTML parsing
        bs4_status = self.check_python_package("bs4")
        optional_deps.append(
            DependencyInfo(
                name="beautifulsoup4",
                status=bs4_status,
                description="Python package: beautifulsoup4 (HTML parsing)",
                install_command="pip install beautifulsoup4",
                impact="HTML parsing features will be unavailable",
                is_critical=False,
            )
        )

        return ToolDependencies(
            tool_name="Search Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_research_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Research Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages
        python_packages = ["spacy", "scipy", "nltk"]
        for pkg in python_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} functionality will be unavailable",
                    is_critical=True,
                )
            )

        # spaCy models
        spacy_models = ["en_core_web_sm"]
        for model in spacy_models:
            status = self._check_spacy_model(model)
            model_deps.append(
                DependencyInfo(
                    name=f"spaCy {model}",
                    status=status,
                    description=f"spaCy model: {model}",
                    install_command=f"python -m spacy download {model}",
                    impact=f"Text analysis in English will be unavailable",
                    is_critical=True,
                )
            )

        # NLTK data
        nltk_data = ["stopwords", "punkt", "wordnet", "averaged_perceptron_tagger"]
        for data in nltk_data:
            status = self._check_nltk_data(data)
            install_cmd = "aiecs-download-nlp-data --download"
            model_deps.append(
                DependencyInfo(
                    name=f"NLTK {data}",
                    status=status,
                    description=f"NLTK data: {data}",
                    install_command=install_cmd,
                    impact=f"NLTK {data} functionality will be unavailable",
                    is_critical=True,
                )
            )

        return ToolDependencies(
            tool_name="Research Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_document_writer_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Document Writer Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages
        core_packages = {
            "python-docx": "docx",
            "openpyxl": "openpyxl",
            "python-pptx": "pptx",
            "pillow": "PIL",
        }
        for pkg_name, import_name in core_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} document writing functionality will be unavailable",
                    is_critical=True,
                )
            )

        # Pillow system dependencies
        pillow_status = self._check_pillow_system_deps()
        system_deps.append(
            DependencyInfo(
                name="Pillow System Libraries",
                status=pillow_status,
                description="System libraries for image processing (libjpeg, libpng, etc.)",
                install_command=self._get_pillow_system_deps_command(),
                impact="Image processing in documents may be limited",
                is_critical=False,
            )
        )

        # Optional: XlsxWriter for advanced Excel features
        xlsxwriter_status = self.check_python_package("xlsxwriter")
        optional_deps.append(
            DependencyInfo(
                name="xlsxwriter",
                status=xlsxwriter_status,
                description="Python package: xlsxwriter (Advanced Excel writing)",
                install_command="pip install xlsxwriter",
                impact="Advanced Excel features will be unavailable",
                is_critical=False,
            )
        )

        return ToolDependencies(
            tool_name="Document Writer Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_statistical_analyzer_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Statistical Analyzer Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages
        core_packages = {
            "pandas": "pandas",
            "numpy": "numpy",
            "scipy": "scipy",
            "statsmodels": "statsmodels",
            "scikit-learn": "sklearn",
        }
        for pkg_name, import_name in core_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} statistical methods will be unavailable",
                    is_critical=True,
                )
            )

        # Optional: matplotlib for visualization
        matplotlib_status = self.check_python_package("matplotlib")
        optional_deps.append(
            DependencyInfo(
                name="matplotlib",
                status=matplotlib_status,
                description="Python package: matplotlib (Statistical visualization)",
                install_command="pip install matplotlib",
                impact="Statistical visualization features will be unavailable",
                is_critical=False,
            )
        )

        # Optional: seaborn for advanced visualization
        seaborn_status = self.check_python_package("seaborn")
        optional_deps.append(
            DependencyInfo(
                name="seaborn",
                status=seaborn_status,
                description="Python package: seaborn (Advanced statistical visualization)",
                install_command="pip install seaborn",
                impact="Advanced visualization features will be unavailable",
                is_critical=False,
            )
        )

        return ToolDependencies(
            tool_name="Statistical Analyzer Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_data_profiler_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Data Profiler Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages
        core_packages = ["pandas", "numpy", "scipy"]
        for pkg in core_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} data profiling functionality will be unavailable",
                    is_critical=True,
                )
            )

        # Optional: ydata-profiling for comprehensive profiling
        ydata_status = self.check_python_package("ydata_profiling")
        optional_deps.append(
            DependencyInfo(
                name="ydata-profiling",
                status=ydata_status,
                description="Python package: ydata-profiling (Comprehensive data profiling)",
                install_command="pip install ydata-profiling",
                impact="Comprehensive profiling reports will be unavailable",
                is_critical=False,
            )
        )

        # Optional: matplotlib for visualization
        matplotlib_status = self.check_python_package("matplotlib")
        optional_deps.append(
            DependencyInfo(
                name="matplotlib",
                status=matplotlib_status,
                description="Python package: matplotlib (Profile visualization)",
                install_command="pip install matplotlib",
                impact="Visual profiling features will be unavailable",
                is_critical=False,
            )
        )

        return ToolDependencies(
            tool_name="Data Profiler Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_data_transformer_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Data Transformer Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages
        core_packages = {
            "pandas": "pandas",
            "numpy": "numpy",
            "scikit-learn": "sklearn",
        }
        for pkg_name, import_name in core_packages.items():
            status = self.check_python_package(import_name)
            python_deps.append(
                DependencyInfo(
                    name=pkg_name,
                    status=status,
                    description=f"Python package: {pkg_name}",
                    install_command=f"pip install {pkg_name}",
                    impact=f"{pkg_name} data transformation functionality will be unavailable",
                    is_critical=True,
                )
            )

        # Optional: scipy for advanced transformations
        scipy_status = self.check_python_package("scipy")
        optional_deps.append(
            DependencyInfo(
                name="scipy",
                status=scipy_status,
                description="Python package: scipy (Advanced transformations)",
                install_command="pip install scipy",
                impact="Advanced transformation methods will be unavailable",
                is_critical=False,
            )
        )

        # Optional: category_encoders for categorical encoding
        catencoder_status = self.check_python_package("category_encoders")
        optional_deps.append(
            DependencyInfo(
                name="category_encoders",
                status=catencoder_status,
                description="Python package: category_encoders (Advanced categorical encoding)",
                install_command="pip install category_encoders",
                impact="Advanced encoding methods will be unavailable",
                is_critical=False,
            )
        )

        return ToolDependencies(
            tool_name="Data Transformer Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_generic_tool_dependencies(self, tool_name: str, display_name: str) -> ToolDependencies:
        """
        Generic dependency check for simple tools (mainly orchestrators).
        These tools typically only require basic Python dependencies.
        """
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Basic Python packages common to all tools
        python_packages = ["pydantic"]
        for pkg in python_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} functionality will be unavailable",
                    is_critical=True,
                )
            )

        return ToolDependencies(
            tool_name=display_name,
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_kg_builder_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Knowledge Graph Builder Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages
        core_packages = ["pydantic", "networkx"]
        for pkg in core_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} graph building functionality will be unavailable",
                    is_critical=True,
                )
            )

        # Optional: Neo4j for graph database
        neo4j_status = self.check_python_package("neo4j")
        optional_deps.append(
            DependencyInfo(
                name="neo4j",
                status=neo4j_status,
                description="Python package: neo4j (Graph database support)",
                install_command="pip install neo4j",
                impact="Neo4j graph database features will be unavailable",
                is_critical=False,
            )
        )

        return ToolDependencies(
            tool_name="Knowledge Graph Builder Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_graph_search_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Graph Search Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages
        core_packages = ["pydantic", "networkx"]
        for pkg in core_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} graph search functionality will be unavailable",
                    is_critical=True,
                )
            )

        return ToolDependencies(
            tool_name="Graph Search Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_graph_reasoning_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Graph Reasoning Tool."""
        system_deps: List[DependencyInfo] = []
        python_deps: List[DependencyInfo] = []
        model_deps: List[DependencyInfo] = []
        optional_deps: List[DependencyInfo] = []

        # Core Python packages
        core_packages = ["pydantic", "networkx"]
        for pkg in core_packages:
            status = self.check_python_package(pkg)
            python_deps.append(
                DependencyInfo(
                    name=pkg,
                    status=status,
                    description=f"Python package: {pkg}",
                    install_command=f"pip install {pkg}",
                    impact=f"{pkg} graph reasoning functionality will be unavailable",
                    is_critical=True,
                )
            )

        return ToolDependencies(
            tool_name="Graph Reasoning Tool",
            system_deps=system_deps,
            python_deps=python_deps,
            model_deps=model_deps,
            optional_deps=optional_deps,
        )

    def check_document_layout_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Document Layout Tool."""
        return self.check_generic_tool_dependencies("document_layout", "Document Layout Tool")

    def check_content_insertion_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Content Insertion Tool."""
        return self.check_generic_tool_dependencies("content_insertion", "Content Insertion Tool")

    def check_document_creator_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for Document Creator Tool."""
        return self.check_generic_tool_dependencies("document_creator", "Document Creator Tool")

    def check_ai_document_writer_orchestrator_dependencies(self) -> ToolDependencies:
        """Check dependencies for AI Document Writer Orchestrator."""
        return self.check_generic_tool_dependencies("ai_document_writer_orchestrator", "AI Document Writer Orchestrator")

    def check_ai_document_orchestrator_dependencies(self) -> ToolDependencies:
        """Check dependencies for AI Document Orchestrator."""
        return self.check_generic_tool_dependencies("ai_document_orchestrator", "AI Document Orchestrator")

    def check_ai_insight_generator_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for AI Insight Generator Tool."""
        return self.check_generic_tool_dependencies("ai_insight_generator", "AI Insight Generator Tool")

    def check_ai_data_analysis_orchestrator_dependencies(self) -> ToolDependencies:
        """Check dependencies for AI Data Analysis Orchestrator."""
        return self.check_generic_tool_dependencies("ai_data_analysis_orchestrator", "AI Data Analysis Orchestrator")

    def check_ai_report_orchestrator_tool_dependencies(self) -> ToolDependencies:
        """Check dependencies for AI Report Orchestrator Tool."""
        return self.check_generic_tool_dependencies("ai_report_orchestrator", "AI Report Orchestrator Tool")

    def check_all_dependencies(self) -> Dict[str, ToolDependencies]:
        """Check all tool dependencies."""
        self.logger.info("Starting comprehensive dependency check...")

        tools = {
            # Task tools (11 total)
            "image": self.check_image_tool_dependencies(),
            "classifier": self.check_classfire_tool_dependencies(),  # Note: registered as "classifier"
            "office": self.check_office_tool_dependencies(),
            "stats": self.check_stats_tool_dependencies(),
            "report": self.check_report_tool_dependencies(),
            "scraper": self.check_scraper_tool_dependencies(),
            "chart": self.check_chart_tool_dependencies(),
            "pandas": self.check_pandas_tool_dependencies(),
            "apisource": self.check_apisource_tool_dependencies(),
            "search": self.check_search_tool_dependencies(),
            "research": self.check_research_tool_dependencies(),
            
            # Document tools (7 total)
            "document_parser": self.check_document_parser_tool_dependencies(),
            "document_writer": self.check_document_writer_tool_dependencies(),
            "document_layout": self.check_document_layout_tool_dependencies(),
            "content_insertion": self.check_content_insertion_tool_dependencies(),
            "document_creator": self.check_document_creator_tool_dependencies(),
            "ai_document_writer_orchestrator": self.check_ai_document_writer_orchestrator_dependencies(),
            "ai_document_orchestrator": self.check_ai_document_orchestrator_dependencies(),
            
            # Statistics tools (9 total)
            "data_loader": self.check_data_loader_tool_dependencies(),
            "data_visualizer": self.check_data_visualizer_tool_dependencies(),
            "model_trainer": self.check_model_trainer_tool_dependencies(),
            "statistical_analyzer": self.check_statistical_analyzer_tool_dependencies(),
            "data_profiler": self.check_data_profiler_tool_dependencies(),
            "data_transformer": self.check_data_transformer_tool_dependencies(),
            "ai_insight_generator": self.check_ai_insight_generator_tool_dependencies(),
            "ai_data_analysis_orchestrator": self.check_ai_data_analysis_orchestrator_dependencies(),
            "ai_report_orchestrator": self.check_ai_report_orchestrator_tool_dependencies(),
            
            # Knowledge graph tools (3 total)
            "kg_builder": self.check_kg_builder_tool_dependencies(),
            "graph_search": self.check_graph_search_tool_dependencies(),
            "graph_reasoning": self.check_graph_reasoning_tool_dependencies(),
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
        with open(filename, "w", encoding="utf-8") as f:
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
        1 for tool_deps in tools.values() for dep in tool_deps.system_deps + tool_deps.python_deps + tool_deps.model_deps if dep.status != DependencyStatus.AVAILABLE and dep.is_critical
    )

    if critical_issues == 0:
        print("\n✅ All critical dependencies are available!")
        return 0
    else:
        print(f"\n❌ {critical_issues} critical dependencies are missing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
