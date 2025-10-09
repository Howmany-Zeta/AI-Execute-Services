#!/usr/bin/env python3
"""
Automated script to download required NLP data for AIECS ClassifierTool.

This script downloads:
1. NLTK stopwords data package for keyword extraction
2. spaCy English model (en_core_web_sm) for text processing
3. spaCy Chinese model (zh_core_web_sm) for Chinese text processing
"""

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple, Optional


def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('nlp_data_download.log')
        ]
    )
    return logging.getLogger(__name__)


def run_command(cmd: List[str], logger: logging.Logger) -> Tuple[bool, str]:
    """
    Run a shell command and return success status and output.
    
    Args:
        cmd: List of command arguments
        logger: Logger instance
    
    Returns:
        Tuple of (success, output)
    """
    try:
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True
        )
        logger.info(f"Command succeeded: {result.stdout}")
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed with exit code {e.returncode}: {e.stderr}"
        logger.error(error_msg)
        return False, error_msg
    except FileNotFoundError:
        error_msg = f"Command not found: {cmd[0]}"
        logger.error(error_msg)
        return False, error_msg


def check_python_package(package_name: str, logger: logging.Logger) -> bool:
    """
    Check if a Python package is installed.
    
    Args:
        package_name: Name of the package to check
        logger: Logger instance
        
    Returns:
        True if package is installed, False otherwise
    """
    try:
        __import__(package_name)
        logger.info(f"Package {package_name} is already installed")
        return True
    except ImportError:
        logger.warning(f"Package {package_name} is not installed")
        return False


def download_nltk_data(logger: logging.Logger) -> bool:
    """
    Download required NLTK data packages.
    
    Args:
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Starting NLTK data download...")
    
    if not check_python_package('nltk', logger):
        logger.error("NLTK is not installed. Please install it first with: pip install nltk")
        return False
    
    try:
        import nltk
        
        # Download required NLTK data
        packages_to_download = [
            'stopwords',
            'punkt',
            'punkt_tab',  # Added for RAKE-NLTK compatibility
            'wordnet',
            'averaged_perceptron_tagger'
        ]
        
        for package in packages_to_download:
            try:
                logger.info(f"Downloading NLTK package: {package}")
                nltk.download(package, quiet=True)
                logger.info(f"Successfully downloaded NLTK package: {package}")
            except Exception as e:
                logger.error(f"Failed to download NLTK package {package}: {e}")
                return False
                
        logger.info("All NLTK data packages downloaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading NLTK data: {e}")
        return False


def download_spacy_model(model_name: str, logger: logging.Logger) -> bool:
    """
    Download a spaCy model.
    
    Args:
        model_name: Name of the spaCy model to download
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Starting spaCy model download: {model_name}")
    
    if not check_python_package('spacy', logger):
        logger.error("spaCy is not installed. Please install it first with: pip install spacy")
        return False
    
    # Check if model is already installed
    try:
        import spacy
        spacy.load(model_name)
        logger.info(f"spaCy model {model_name} is already installed")
        return True
    except OSError:
        # Model not installed, proceed with download
        pass
    except Exception as e:
        logger.error(f"Error checking spaCy model {model_name}: {e}")
        return False
    
    # Download the model
    cmd = [sys.executable, "-m", "spacy", "download", model_name]
    success, output = run_command(cmd, logger)
    
    if success:
        logger.info(f"Successfully downloaded spaCy model: {model_name}")
        
        # Verify the model can be loaded
        try:
            import spacy
            spacy.load(model_name)
            logger.info(f"Verified spaCy model {model_name} can be loaded")
            return True
        except Exception as e:
            logger.error(f"Downloaded model {model_name} cannot be loaded: {e}")
            return False
    else:
        logger.error(f"Failed to download spaCy model {model_name}: {output}")
        return False
    

def download_spacy_pkuseg_model(logger: logging.Logger) -> bool:
    """
    Download and install spaCy PKUSeg model for Chinese text segmentation.

    Args:
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    logger.info("Starting spaCy PKUSeg model installation...")

    if not check_python_package('spacy', logger):
        logger.error("spaCy is not installed. Please install it first with: pip install spacy")
        return False

    # Check if spacy_pkuseg is already installed
    if check_python_package('spacy_pkuseg', logger):
        logger.info("spacy_pkuseg is already installed")
        return True

    # Install spacy_pkuseg package
    cmd = [sys.executable, "-m", "pip", "install", "spacy_pkuseg"]
    success, output = run_command(cmd, logger)

    if success:
        logger.info("Successfully installed spacy_pkuseg")

        # Verify the package can be imported
        try:
            import spacy_pkuseg
            logger.info("Verified spacy_pkuseg can be imported")

            # Test basic functionality
            seg = spacy_pkuseg.pkuseg()
            test_result = seg.cut("这是一个测试句子")
            logger.info(f"spacy_pkuseg test successful: {list(test_result)}")
            return True
        except Exception as e:
            logger.error(f"Installed spacy_pkuseg cannot be used: {e}")
            return False
    else:
        logger.error(f"Failed to install spacy_pkuseg: {output}")
        return False


def download_rake_nltk_data(logger: logging.Logger) -> bool:
    """
    Ensure RAKE-NLTK has required data.
    
    Args:
        logger: Logger instance
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Checking RAKE-NLTK data...")
    
    if not check_python_package('rake_nltk', logger):
        logger.warning("RAKE-NLTK is not installed. This is optional for English keyword extraction.")
        return True  # Not critical, return True
    
    try:
        from rake_nltk import Rake
        # Test RAKE functionality
        rake = Rake()
        rake.extract_keywords_from_text("This is a test sentence for RAKE.")
        keywords = rake.get_ranked_phrases()
        logger.info("RAKE-NLTK is working correctly")
        return True
    except Exception as e:
        logger.warning(f"RAKE-NLTK test failed: {e}. This is not critical.")
        return True  # Not critical, return True


def verify_installation(logger: logging.Logger) -> bool:
    """
    Verify all NLP components are properly installed.
    
    Args:
        logger: Logger instance
        
    Returns:
        True if all components work, False otherwise
    """
    logger.info("Verifying NLP data installation...")
    
    success = True
    
    # Test NLTK
    try:
        import nltk
        from nltk.corpus import stopwords
        english_stopwords = stopwords.words('english')
        logger.info(f"NLTK verification successful. Loaded {len(english_stopwords)} English stopwords")
    except Exception as e:
        logger.error(f"NLTK verification failed: {e}")
        success = False
    
    # Test spaCy English model
    try:
        import spacy
        nlp_en = spacy.load('en_core_web_sm')
        doc = nlp_en("This is a test sentence.")
        logger.info(f"spaCy English model verification successful. Processed {len(doc)} tokens")
    except Exception as e:
        logger.error(f"spaCy English model verification failed: {e}")
        success = False
    
    # Test spaCy Chinese model (optional)
    try:
        import spacy
        nlp_zh = spacy.load('zh_core_web_sm')
        doc = nlp_zh("这是一个测试句子。")
        logger.info(f"spaCy Chinese model verification successful. Processed {len(doc)} tokens")
    except Exception as e:
        logger.warning(f"spaCy Chinese model verification failed: {e}. This is optional.")

    # Test spaCy PKUSeg model (optional)
    try:
        import spacy_pkuseg
        seg = spacy_pkuseg.pkuseg()
        result = list(seg.cut("这是一个测试句子"))
        logger.info(f"spaCy PKUSeg model verification successful. Segmented: {result}")
    except Exception as e:
        logger.warning(f"spaCy PKUSeg model verification failed: {e}. This is optional.")

    return success


def download_all_nlp_data():
    """Download all required NLP data."""
    logger = setup_logging()
    logger.info("Starting AIECS NLP data download process...")

    success = True

    # Download NLTK data
    if not download_nltk_data(logger):
        success = False

    # Download spaCy English model
    if not download_spacy_model('en_core_web_sm', logger):
        success = False

    # Download spaCy Chinese model (optional)
    if not download_spacy_model('zh_core_web_sm', logger):
        logger.warning("Chinese model download failed, but this is optional")
        # Don't mark as failure for Chinese model

    # Download spaCy Chinese segmentation model (optional)
    if not download_spacy_pkuseg_model(logger):
        logger.warning("spaCy PKUSeg model download failed, but this is optional")
        # Don't mark as failure for PKUSeg model

    # Check RAKE-NLTK (optional)
    download_rake_nltk_data(logger)

    # Verify installation
    if success and verify_installation(logger):
        logger.info("✅ All NLP data downloaded and verified successfully!")
        logger.info("AIECS ClassifierTool is ready to use.")
        return 0
    else:
        logger.error("❌ Some NLP data downloads failed. Please check the logs above.")
        logger.error("You may need to install missing packages or run this script again.")
        return 1


def main():
    """Main entry point with argument parsing."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Download NLP data for AIECS tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show this help message
  aiecs-download-nlp-data --help

  # Download all NLP data
  aiecs-download-nlp-data --download
  aiecs-download-nlp-data -d

NLP Data Includes:
  - NLTK packages: stopwords, punkt, wordnet, averaged_perceptron_tagger
  - spaCy models: en_core_web_sm (English), zh_core_web_sm (Chinese, optional)
  - spaCy PKUSeg model (Chinese segmentation, optional)
  - RAKE-NLTK data (keyword extraction, optional)
        """
    )

    parser.add_argument(
        '-d', '--download',
        action='store_true',
        help='Download all NLP data packages'
    )

    args = parser.parse_args()

    # If no arguments provided, show help
    if not args.download:
        parser.print_help()
        print("\n⚠️  No action specified. Use --download or -d to download NLP data.")
        return 0

    # Execute download
    return download_all_nlp_data()


if __name__ == "__main__":
    sys.exit(main())