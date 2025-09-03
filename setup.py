"""
Setup script for AIECS with post-install hook for weasel patch
"""

import os
import sys
from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.develop import develop


def run_post_install():
    """Run post-installation tasks"""
    print("\n" + "="*60)
    print("AIECS Post-Installation Setup")
    print("="*60 + "\n")
    
    # Track installation results
    weasel_success = False
    nlp_success = False
    
    # Run weasel patch
    try:
        from aiecs.scripts.fix_weasel_validator import main as fix_weasel
        print("Running weasel library patch...")
        fix_weasel()
        weasel_success = True
        print("✅ Weasel patch applied successfully!")
    except Exception as e:
        print(f"⚠️  Warning: Could not apply weasel patch automatically: {e}")
        print("You can run it manually later with: aiecs-patch-weasel")
    
    # Run NLP data download
    try:
        from aiecs.scripts.download_nlp_data import main as download_nlp_data
        print("\nDownloading required NLP data (NLTK stopwords, spaCy model)...")
        exit_code = download_nlp_data()
        if exit_code == 0:
            nlp_success = True
            print("✅ NLP data download completed successfully!")
        elif exit_code is None:
            print("⚠️  NLP data download completed with warnings (see above)")
        else:
            print("❌ NLP data download failed")
    except Exception as e:
        print(f"⚠️  Warning: Could not download NLP data automatically: {e}")
        print("You can run it manually later with: python -m aiecs.scripts.download_nlp_data")
    
    # Summary
    print("\n" + "="*60)
    print("Post-installation Summary:")
    print(f"  • Weasel patch: {'✅ Success' if weasel_success else '⚠️  Warning (manual action required)'}")
    print(f"  • NLP data:     {'✅ Success' if nlp_success else '⚠️  Warning (manual action required)'}")
    
    if weasel_success and nlp_success:
        print("\n🎉 All post-installation tasks completed successfully!")
    else:
        print("\n⚠️  Some tasks completed with warnings. AIECS will still work,")
        print("but you may need to install some dependencies manually as needed.")
    
    print("="*60 + "\n")


class PostInstallCommand(install):
    """Post-installation for installation mode"""
    def run(self):
        install.run(self)
        run_post_install()


class PostDevelopCommand(develop):
    """Post-installation for development mode"""
    def run(self):
        develop.run(self)
        run_post_install()


# Read long description from README
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Setup configuration
setup(
    name="aiecs",
    version="1.0.0",
    author="AIECS Team",
    author_email="iretbl@gmail.com",
    description="AI Execute Services - A middleware framework for AI-powered task execution and tool orchestration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aiecs-team/aiecs",
    project_urls={
        "Bug Tracker": "https://github.com/aiecs-team/aiecs/issues",
        "Documentation": "https://aiecs.readthedocs.io",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
        "Framework :: Celery",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    packages=find_packages(include=["aiecs", "aiecs.*"]),
    package_data={
        "aiecs": [
            "scripts/*",
            "scripts/**/*",
        ],
    },
    include_package_data=True,
    python_requires=">=3.10,<3.13",
    install_requires=[
        # Core dependencies - Web framework and API
        "fastapi>=0.115.12,<0.116.0",
        "httpx>=0.28.1,<0.29.0",
        "uvicorn[standard]>=0.34.2,<0.35.0",
        "python-dotenv>=1.1.0,<2.0.0",
        "pydantic>=2.11.5,<3.0.0",
        "pydantic-settings>=2.9.1,<3.0.0",
        "cachetools>=5.0.0,<6.0.0",
        # Messaging and task queue
        "celery>=5.5.2,<6.0.0",
        "redis>=6.2.0,<7.0.0",
        "python-socketio>=5.13.0,<6.0.0",
        "python-engineio>=4.12.1,<5.0.0",
        "tenacity>=9.1.2,<10.0.0",
        # LLM and AI services
        "openai>=1.68.2,<1.76.0",
        "google-cloud-aiplatform>=1.71.1,<2.0.0",
        # NLP and text processing
        "spacy>=3.8.7,<4.0.0",
        "rake-nltk>=1.0.6,<2.0.0",
        # Data processing and analysis
        "numpy>=2.2.6,<3.0.0",
        "pandas>=2.2.3,<3.0.0",
        "scipy>=1.15.3,<2.0.0",
        "scikit-learn>=1.5.0,<2.0.0",
        # Document processing
        "pyyaml>=6.0.2,<7.0.0",
        "python-docx>=1.1.2,<2.0.0",
        "python-pptx>=1.0.2,<2.0.0",
        "markdown>=3.8,<4.0",
        "bleach>=6.2.0,<7.0.0",
        # File operations
        "typing-extensions>=4.13.2,<5.0.0",
        # Visualization and reporting
        "matplotlib>=3.10.3,<4.0.0",
        "seaborn>=0.13.2,<0.14.0",
        "pyreadstat>=1.2.9,<2.0.0",
        "statsmodels>=0.14.4,<0.15.0",
        "jinja2>=3.1.6,<4.0.0",
        # Web scraping and HTTP
        "beautifulsoup4>=4.13.4,<5.0.0",
        "lxml>=5.4.0,<6.0.0",
        "playwright>=1.52.0,<2.0.0",
        "pytesseract>=0.3.13,<0.4.0",
        "pillow>=11.2.1,<12.0.0",
        "tika>=2.6.0,<3.0.0",
        # Database drivers
        "asyncpg>=0.30.0,<1.0.0",
        # Monitoring and metrics
        "prometheus-client>=0.21.1,<1.0.0",
        # Distributed tracing
        "jaeger-client>=4.8.0,<5.0.0",
        "opentracing>=2.4.0,<3.0.0",
        "sqlalchemy>=2.0.41,<3.0.0",
        "flower>=2.0.1,<3.0.0",
        "psutil>=7.0.0,<8.0.0",
        "aiofiles>=24.1.0,<25.0.0",
        "langchain>=0.3.26,<0.4.0",
        "langgraph>=0.5.3,<0.6.0",
        "weasel==0.4.1",
        "pdfplumber>=0.11.7,<0.12.0",
        "pdfminer-six==20250506",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.5",
            "pytest-asyncio>=1.0.0",
            "pytest-cov>=4.0.0",
            "pytest-xdist>=3.0.0",
            "pytest-mock>=3.10.0",
            "black>=25.1.0",
            "flake8>=7.2.0",
            "mypy>=1.15.0",
            "bump-pydantic>=0.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "aiecs=aiecs.__main__:main",
            "aiecs-patch-weasel=aiecs.scripts.fix_weasel_validator:main",
            "aiecs-download-nlp-data=aiecs.scripts.download_nlp_data:main",
        ],
    },
    cmdclass={
        'install': PostInstallCommand,
        'develop': PostDevelopCommand,
    },
    keywords=["ai", "middleware", "llm", "orchestration", "async", "tools"],
)
