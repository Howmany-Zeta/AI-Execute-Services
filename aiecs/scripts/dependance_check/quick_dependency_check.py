#!/usr/bin/env python3
"""
Quick dependency checker for AIECS post-installation.

This script performs a fast check of critical dependencies and provides
installation guidance for missing components.
"""

import os
import sys
import subprocess
import platform
import logging
from typing import Dict, List, Tuple, Optional


class QuickDependencyChecker:
    """Quick dependency checker for post-installation."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.system = platform.system().lower()
        self.issues = []
        self.critical_issues = []
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(levelname)s: %(message)s'
        )
        return logging.getLogger(__name__)
    
    def check_command(self, command: str, version_flag: str = "--version") -> bool:
        """Check if a system command is available."""
        try:
            result = subprocess.run(
                [command, version_flag],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
            return False
    
    def check_python_package(self, package_name: str) -> bool:
        """Check if a Python package is installed."""
        try:
            __import__(package_name)
            return True
        except ImportError:
            return False
    
    def check_critical_dependencies(self) -> Dict[str, bool]:
        """Check critical dependencies that affect core functionality."""
        results = {}
        
        # Core Python packages
        core_packages = [
            "fastapi", "uvicorn", "pydantic", "httpx", "celery", "redis",
            "pandas", "numpy", "scipy", "scikit-learn", "matplotlib"
        ]
        
        for pkg in core_packages:
            results[f"python_{pkg}"] = self.check_python_package(pkg)
            if not results[f"python_{pkg}"]:
                self.critical_issues.append(f"Missing Python package: {pkg}")
        
        # System dependencies for tools
        system_deps = {
            "java": ("Java Runtime Environment", "java", "-version"),
            "tesseract": ("Tesseract OCR", "tesseract", "--version"),
        }
        
        for key, (name, cmd, flag) in system_deps.items():
            results[f"system_{key}"] = self.check_command(cmd, flag)
            if not results[f"system_{key}"]:
                self.issues.append(f"Missing system dependency: {name}")
        
        return results
    
    def check_tool_specific_dependencies(self) -> Dict[str, Dict[str, bool]]:
        """Check dependencies for specific tools."""
        tool_results = {}
        
        # Image Tool dependencies
        image_deps = {
            "tesseract": self.check_command("tesseract"),
            "PIL": self.check_python_package("PIL"),
            "pytesseract": self.check_python_package("pytesseract"),
        }
        tool_results["image"] = image_deps
        
        # ClassFire Tool dependencies
        classfire_deps = {
            "spacy": self.check_python_package("spacy"),
            "nltk": self.check_python_package("nltk"),
            "transformers": self.check_python_package("transformers"),
        }
        tool_results["classfire"] = classfire_deps
        
        # Office Tool dependencies
        office_deps = {
            "java": self.check_command("java"),
            "tika": self.check_python_package("tika"),
            "python-docx": self.check_python_package("python-docx"),
            "openpyxl": self.check_python_package("openpyxl"),
        }
        tool_results["office"] = office_deps
        
        # Stats Tool dependencies
        stats_deps = {
            "pandas": self.check_python_package("pandas"),
            "pyreadstat": self.check_python_package("pyreadstat"),
            "statsmodels": self.check_python_package("statsmodels"),
        }
        tool_results["stats"] = stats_deps
        
        # Report Tool dependencies
        report_deps = {
            "jinja2": self.check_python_package("jinja2"),
            "matplotlib": self.check_python_package("matplotlib"),
            "weasyprint": self.check_python_package("weasyprint"),
        }
        tool_results["report"] = report_deps
        
        # Scraper Tool dependencies
        scraper_deps = {
            "playwright": self.check_python_package("playwright"),
            "beautifulsoup4": self.check_python_package("beautifulsoup4"),
            "scrapy": self.check_python_package("scrapy"),
        }
        tool_results["scraper"] = scraper_deps
        
        return tool_results
    
    def get_installation_commands(self) -> Dict[str, List[str]]:
        """Get installation commands for missing dependencies."""
        commands = {
            "system": [],
            "python": [],
            "models": []
        }
        
        # System dependencies
        if self.system == "linux":
            if not self.check_command("java"):
                commands["system"].append("sudo apt-get install openjdk-11-jdk")
            if not self.check_command("tesseract"):
                commands["system"].append("sudo apt-get install tesseract-ocr tesseract-ocr-eng")
        elif self.system == "darwin":
            if not self.check_command("java"):
                commands["system"].append("brew install openjdk@11")
            if not self.check_command("tesseract"):
                commands["system"].append("brew install tesseract")
        
        # Python packages (these should already be installed via pip)
        missing_packages = []
        for issue in self.critical_issues:
            if "Missing Python package:" in issue:
                pkg = issue.split(": ")[1]
                missing_packages.append(pkg)
        
        if missing_packages:
            commands["python"].append(f"pip install {' '.join(missing_packages)}")
        
        # Models and data
        commands["models"].append("python -m aiecs.scripts.download_nlp_data")
        commands["models"].append("playwright install")
        
        return commands
    
    def generate_quick_report(self) -> str:
        """Generate a quick dependency report."""
        report = []
        report.append("🔍 AIECS Quick Dependency Check")
        report.append("=" * 50)
        
        # Check critical dependencies
        critical_results = self.check_critical_dependencies()
        tool_results = self.check_tool_specific_dependencies()
        
        # Critical dependencies status
        report.append("\n📦 Critical Dependencies:")
        critical_ok = all(critical_results.values())
        if critical_ok:
            report.append("✅ All critical dependencies are available")
        else:
            report.append("❌ Some critical dependencies are missing")
            for key, available in critical_results.items():
                if not available:
                    dep_name = key.replace("python_", "").replace("system_", "")
                    report.append(f"   ❌ {dep_name}")
        
        # Tool-specific dependencies
        report.append("\n🔧 Tool-Specific Dependencies:")
        for tool, deps in tool_results.items():
            tool_ok = all(deps.values())
            status = "✅" if tool_ok else "⚠️"
            report.append(f"   {status} {tool.title()} Tool")
            
            if not tool_ok:
                for dep, available in deps.items():
                    if not available:
                        report.append(f"      ❌ {dep}")
        
        # Installation commands
        commands = self.get_installation_commands()
        if any(commands.values()):
            report.append("\n🛠️  Installation Commands:")
            
            if commands["system"]:
                report.append("   System Dependencies:")
                for cmd in commands["system"]:
                    report.append(f"      {cmd}")
            
            if commands["python"]:
                report.append("   Python Packages:")
                for cmd in commands["python"]:
                    report.append(f"      {cmd}")
            
            if commands["models"]:
                report.append("   Models and Data:")
                for cmd in commands["models"]:
                    report.append(f"      {cmd}")
        
        # Summary
        total_issues = len(self.issues) + len(self.critical_issues)
        if total_issues == 0:
            report.append("\n🎉 All dependencies are available!")
            report.append("AIECS is ready to use with full functionality.")
        else:
            report.append(f"\n⚠️  Found {total_issues} dependency issues.")
            if self.critical_issues:
                report.append(f"   Critical: {len(self.critical_issues)}")
            if self.issues:
                report.append(f"   Optional: {len(self.issues)}")
            report.append("Please install missing dependencies for full functionality.")
        
        return "\n".join(report)
    
    def run_check(self) -> int:
        """Run the quick dependency check."""
        print("🔍 Running quick dependency check...")
        
        # Generate and display report
        report = self.generate_quick_report()
        print(report)
        
        # Return exit code
        if self.critical_issues:
            return 1
        else:
            return 0


def main():
    """Main function."""
    checker = QuickDependencyChecker()
    return checker.run_check()


if __name__ == "__main__":
    sys.exit(main())





