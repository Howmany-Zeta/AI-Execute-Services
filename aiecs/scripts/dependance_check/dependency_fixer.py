#!/usr/bin/env python3
"""
Dependency fixer for AIECS tools.

This script automatically installs missing dependencies based on the
dependency checker results.
"""

import sys
import os
import subprocess
import platform
import logging
from pathlib import Path
from typing import Dict, List, Optional


class DependencyFixer:
    """Automatic dependency fixer for AIECS."""

    def __init__(self, interactive: bool = True):
        self.logger = self._setup_logging()
        self.system = platform.system().lower()
        self.interactive = interactive
        self.fixes_applied: List[str] = []
        self.fixes_failed: List[str] = []

    def _setup_logging(self) -> logging.Logger:
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("dependency_fix.log"),
            ],
        )
        return logging.getLogger(__name__)

    def _get_environment_path(self) -> Optional[Path]:
        """
        Get the path to the current Python environment (virtual environment or Poetry environment).

        Returns:
            Path to the environment if found, None otherwise
        """
        # Check VIRTUAL_ENV environment variable first (common for venv/virtualenv)
        venv_path = os.environ.get("VIRTUAL_ENV")
        if venv_path:
            env_path = Path(venv_path)
            if env_path.exists():
                self.logger.info(f"Found virtual environment via VIRTUAL_ENV: {env_path}")
                return env_path

        # Check sys.prefix - this points to the virtual environment if we're in one
        # In a virtual environment, sys.prefix != sys.base_prefix
        if sys.prefix != sys.base_prefix:
            env_path = Path(sys.prefix)
            if env_path.exists():
                self.logger.info(f"Found virtual environment via sys.prefix: {env_path}")
                return env_path

        # Check if we're in a Poetry environment by checking sys.executable path
        # Poetry environments are typically in ~/.cache/pypoetry/virtualenvs/ or similar
        exec_path = Path(sys.executable)
        if "pypoetry" in str(exec_path) or exec_path.parts[-3:-1] == ("bin", "python"):
            # Try to find the environment root (go up from bin/python)
            potential_env = exec_path.parent.parent
            if potential_env.exists() and (potential_env / "pyvenv.cfg").exists():
                self.logger.info(f"Found Poetry/virtual environment: {potential_env}")
                return potential_env

        self.logger.warning("No virtual environment detected. NLTK data will be downloaded to user directory.")
        return None

    def _run_command(self, cmd: List[str], description: str) -> bool:
        """Run a command and return success status."""
        try:
            self.logger.info(f"Running: {description}")
            self.logger.info(f"Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300,  # 5 minutes timeout
            )

            self.logger.info(f"Success: {description}")
            if result.stdout:
                self.logger.info(f"Output: {result.stdout}")

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed: {description}")
            self.logger.error(f"Error: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout: {description}")
            return False
        except Exception as e:
            self.logger.error(f"Error: {description} - {e}")
            return False

    def _ask_confirmation(self, message: str) -> bool:
        """Ask for user confirmation if in interactive mode."""
        if not self.interactive:
            return True

        while True:
            response = input(f"{message} (y/n): ").lower().strip()
            if response in ["y", "yes"]:
                return True
            elif response in ["n", "no"]:
                return False
            else:
                print("Please enter 'y' or 'n'")

    def fix_system_dependencies(self, missing_deps: List[str]) -> bool:
        """Fix missing system dependencies."""
        if not missing_deps:
            return True

        self.logger.info("Fixing system dependencies...")

        # Group dependencies by package manager
        apt_packages = []
        brew_packages = []

        for dep in missing_deps:
            if dep == "java":
                if self.system == "linux":
                    apt_packages.append("openjdk-11-jdk")
                elif self.system == "darwin":
                    brew_packages.append("openjdk@11")
            elif dep == "tesseract":
                if self.system == "linux":
                    apt_packages.extend(["tesseract-ocr", "tesseract-ocr-eng"])
                elif self.system == "darwin":
                    brew_packages.append("tesseract")
            elif dep == "tesseract_lang_packs":
                if self.system == "linux":
                    apt_packages.extend(
                        [
                            "tesseract-ocr-chi-sim",
                            "tesseract-ocr-chi-tra",
                            "tesseract-ocr-fra",
                            "tesseract-ocr-deu",
                            "tesseract-ocr-jpn",
                            "tesseract-ocr-kor",
                            "tesseract-ocr-rus",
                            "tesseract-ocr-spa",
                        ]
                    )
            elif dep == "pillow_system_deps":
                if self.system == "linux":
                    apt_packages.extend(
                        [
                            "libjpeg-dev",
                            "zlib1g-dev",
                            "libpng-dev",
                            "libtiff-dev",
                            "libwebp-dev",
                            "libopenjp2-7-dev",
                        ]
                    )
                elif self.system == "darwin":
                    brew_packages.extend(
                        [
                            "libjpeg",
                            "zlib",
                            "libpng",
                            "libtiff",
                            "webp",
                            "openjpeg",
                        ]
                    )
            elif dep == "pyreadstat_deps":
                if self.system == "linux":
                    apt_packages.append("libreadstat-dev")
                elif self.system == "darwin":
                    brew_packages.append("readstat")
            elif dep == "weasyprint_deps":
                if self.system == "linux":
                    apt_packages.extend(
                        [
                            "libcairo2-dev",
                            "libpango1.0-dev",
                            "libgdk-pixbuf2.0-dev",
                            "libffi-dev",
                            "shared-mime-info",
                        ]
                    )
                elif self.system == "darwin":
                    brew_packages.extend(["cairo", "pango", "gdk-pixbuf", "libffi"])
            elif dep == "matplotlib_deps":
                if self.system == "linux":
                    apt_packages.extend(
                        [
                            "libfreetype6-dev",
                            "libpng-dev",
                            "libjpeg-dev",
                            "libtiff-dev",
                            "libwebp-dev",
                        ]
                    )
                elif self.system == "darwin":
                    brew_packages.extend(["freetype", "libpng", "libjpeg", "libtiff", "webp"])

        # Install apt packages
        if apt_packages and self.system == "linux":
            if self._ask_confirmation(f"Install system packages: {', '.join(apt_packages)}?"):
                cmd = ["sudo", "apt-get", "update"]
                if self._run_command(cmd, "Update package list"):
                    cmd = ["sudo", "apt-get", "install", "-y"] + apt_packages
                    if self._run_command(cmd, f"Install packages: {', '.join(apt_packages)}"):
                        self.fixes_applied.append(f"System packages: {', '.join(apt_packages)}")
                    else:
                        self.fixes_failed.append(f"System packages: {', '.join(apt_packages)}")
                        return False

        # Install brew packages
        if brew_packages and self.system == "darwin":
            if self._ask_confirmation(f"Install Homebrew packages: {', '.join(brew_packages)}?"):
                for package in brew_packages:
                    cmd = ["brew", "install", package]
                    if self._run_command(cmd, f"Install {package}"):
                        self.fixes_applied.append(f"Homebrew package: {package}")
                    else:
                        self.fixes_failed.append(f"Homebrew package: {package}")
                        return False

        return True

    def fix_python_dependencies(self, missing_packages: List[str]) -> bool:
        """Fix missing Python packages."""
        if not missing_packages:
            return True

        self.logger.info("Fixing Python dependencies...")

        if self._ask_confirmation(f"Install Python packages: {', '.join(missing_packages)}?"):
            cmd = [sys.executable, "-m", "pip", "install"] + missing_packages
            if self._run_command(cmd, f"Install Python packages: {', '.join(missing_packages)}"):
                self.fixes_applied.append(f"Python packages: {', '.join(missing_packages)}")
                return True
            else:
                self.fixes_failed.append(f"Python packages: {', '.join(missing_packages)}")
                return False

        return True

    def fix_model_dependencies(self, missing_models: List[str]) -> bool:
        """Fix missing model dependencies."""
        if not missing_models:
            return True

        self.logger.info("Fixing model dependencies...")

        # spaCy models
        spacy_models = [m for m in missing_models if m.startswith("spacy_")]
        if spacy_models:
            if self._ask_confirmation(f"Download spaCy models: {', '.join(spacy_models)}?"):
                for model in spacy_models:
                    model_name = model.replace("spacy_", "")
                    cmd = [
                        sys.executable,
                        "-m",
                        "spacy",
                        "download",
                        model_name,
                    ]
                    if self._run_command(cmd, f"Download spaCy model: {model_name}"):
                        self.fixes_applied.append(f"spaCy model: {model_name}")
                    else:
                        self.fixes_failed.append(f"spaCy model: {model_name}")

        # NLTK data
        nltk_data = [m for m in missing_models if m.startswith("nltk_")]
        if nltk_data:
            if self._ask_confirmation(f"Download NLTK data: {', '.join(nltk_data)}?"):
                # Get environment path for environment-specific NLTK data storage
                env_path = self._get_environment_path()
                nltk_data_path: Optional[Path] = None
                original_nltk_data = os.environ.get("NLTK_DATA")

                if env_path:
                    # Create nltk_data directory in the environment
                    nltk_data_path = env_path / "nltk_data"
                    nltk_data_path.mkdir(parents=True, exist_ok=True)
                    self.logger.info(f"Using environment-specific NLTK data directory: {nltk_data_path}")
                else:
                    self.logger.info("No virtual environment detected. Using default NLTK data location (~/nltk_data)")

                for data in nltk_data:
                    data_name = data.replace("nltk_", "")
                    # Build Python command that sets NLTK_DATA if environment path is available
                    if nltk_data_path:
                        # Set NLTK_DATA environment variable in the subprocess
                        python_code = (
                            f"import os; "
                            f"os.environ['NLTK_DATA'] = '{nltk_data_path}'; "
                            f"import nltk; "
                            f"nltk.download('{data_name}', quiet=True)"
                        )
                    else:
                        python_code = f"import nltk; nltk.download('{data_name}', quiet=True)"

                    cmd = [sys.executable, "-c", python_code]
                    if self._run_command(cmd, f"Download NLTK data: {data_name}"):
                        self.fixes_applied.append(f"NLTK data: {data_name}")
                        if nltk_data_path:
                            self.logger.info(f"NLTK data '{data_name}' stored in environment: {nltk_data_path}")
                    else:
                        self.fixes_failed.append(f"NLTK data: {data_name}")

        # Playwright browsers
        if "playwright_browsers" in missing_models:
            if self._ask_confirmation("Install Playwright browsers?"):
                cmd = [sys.executable, "-m", "playwright", "install"]
                if self._run_command(cmd, "Install Playwright browsers"):
                    self.fixes_applied.append("Playwright browsers")
                else:
                    self.fixes_failed.append("Playwright browsers")

        return True

    def fix_dependencies_from_checker(self, checker_results: Dict) -> bool:
        """Fix dependencies based on checker results."""
        self.logger.info("Starting dependency fixing process...")

        # Extract missing dependencies
        missing_system = []
        missing_python = []
        missing_models = []

        for tool_name, tool_deps in checker_results.items():
            if isinstance(tool_deps, dict):
                # Handle tool-specific dependencies
                for dep_type, deps in tool_deps.items():
                    if dep_type == "system_deps":
                        for dep in deps:
                            if dep.status.value == "missing":
                                missing_system.append(dep.name.lower().replace(" ", "_"))
                    elif dep_type == "python_deps":
                        for dep in deps:
                            if dep.status.value == "missing":
                                missing_python.append(dep.name)
                    elif dep_type == "model_deps":
                        for dep in deps:
                            if dep.status.value == "missing":
                                missing_models.append(f"{dep.name.lower().replace(' ', '_')}")

        # Apply fixes
        success = True

        if missing_system:
            if not self.fix_system_dependencies(missing_system):
                success = False

        if missing_python:
            if not self.fix_python_dependencies(missing_python):
                success = False

        if missing_models:
            if not self.fix_model_dependencies(missing_models):
                success = False

        return success

    def generate_fix_report(self) -> str:
        """Generate a report of fixes applied."""
        report = []
        report.append("=" * 60)
        report.append("AIECS DEPENDENCY FIX REPORT")
        report.append("=" * 60)

        if self.fixes_applied:
            report.append("\n✅ Successfully Applied Fixes:")
            for fix in self.fixes_applied:
                report.append(f"  • {fix}")

        if self.fixes_failed:
            report.append("\n❌ Failed Fixes:")
            for fix in self.fixes_failed:
                report.append(f"  • {fix}")

        if not self.fixes_applied and not self.fixes_failed:
            report.append("\nℹ️  No fixes were applied.")

        report.append(f"\nTotal fixes applied: {len(self.fixes_applied)}")
        report.append(f"Total fixes failed: {len(self.fixes_failed)}")

        if self.fixes_failed:
            report.append("\n⚠️  Some fixes failed. Please check the logs and try manual installation.")
        else:
            report.append("\n🎉 All fixes applied successfully!")

        return "\n".join(report)


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Fix AIECS dependencies")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (auto-approve all fixes)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check dependencies, don't fix them",
    )

    args = parser.parse_args()

    # Import and run dependency checker first
    try:
        from aiecs.scripts.dependance_check.dependency_checker import DependencyChecker  # type: ignore[import-untyped]

        checker = DependencyChecker()
        tools = checker.check_all_dependencies()

        if args.check_only:
            report = checker.generate_report(tools)
            print(report)
            return 0

        # Run fixer
        fixer = DependencyFixer(interactive=not args.non_interactive)
        success = fixer.fix_dependencies_from_checker(tools)

        # Generate and display report
        report = fixer.generate_fix_report()
        print(report)

        return 0 if success else 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
