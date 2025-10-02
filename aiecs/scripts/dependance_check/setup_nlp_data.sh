#!/bin/bash
# Setup NLP Data for AIECS ClassifierTool
# This script downloads required NLTK and spaCy data packages

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "=================================================="
echo "AIECS NLP Data Setup"
echo "=================================================="
echo "This script will download required NLP data for:"
echo "  - NLTK stopwords corpus"
echo "  - spaCy English model (en_core_web_sm)"
echo "  - spaCy Chinese model (zh_core_web_sm)"
echo "=================================================="
echo

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to activate virtual environment if it exists
activate_venv() {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo "✅ Virtual environment already active: $VIRTUAL_ENV"
        return 0
    fi
    
    # Check for common virtual environment locations
    local venv_paths=(
        "$PROJECT_ROOT/venv"
        "$PROJECT_ROOT/.venv" 
        "$PROJECT_ROOT/env"
        "$PROJECT_ROOT/.env"
    )
    
    for venv_path in "${venv_paths[@]}"; do
        if [[ -f "$venv_path/bin/activate" ]]; then
            echo "📦 Activating virtual environment: $venv_path"
            source "$venv_path/bin/activate"
            return 0
        fi
    done
    
    echo "⚠️  No virtual environment found. Using system Python."
    return 1
}

# Function to check Python and packages
check_dependencies() {
    echo "🔍 Checking dependencies..."
    
    if ! command_exists python3; then
        echo "❌ Python 3 is not installed or not in PATH"
        exit 1
    fi
    
    local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
    echo "✅ Python version: $python_version"
    
    # Check if we're in the project directory and can import aiecs
    cd "$PROJECT_ROOT"
    if python3 -c "import aiecs" 2>/dev/null; then
        echo "✅ AIECS package is available"
    else
        echo "⚠️  AIECS package not found. You may need to install it first:"
        echo "    pip install -e ."
    fi
}

# Function to run the Python download script
run_download_script() {
    echo
    echo "🚀 Starting NLP data download..."
    echo
    
    cd "$PROJECT_ROOT"
    
    # Try multiple ways to run the script
    if python3 -m aiecs.scripts.download_nlp_data; then
        echo "✅ NLP data download completed successfully!"
        return 0
    elif python3 aiecs/scripts/download_nlp_data.py; then
        echo "✅ NLP data download completed successfully!"
        return 0
    else
        echo "❌ Failed to run NLP data download script"
        return 1
    fi
}

# Function to verify installation
verify_installation() {
    echo
    echo "🔍 Verifying NLP data installation..."
    
    # Test NLTK
    if python3 -c "
import nltk
from nltk.corpus import stopwords
stopwords.words('english')
print('✅ NLTK stopwords data available')
" 2>/dev/null; then
        echo "✅ NLTK verification passed"
    else
        echo "⚠️  NLTK verification failed"
    fi
    
    # Test spaCy English model
    if python3 -c "
import spacy
nlp = spacy.load('en_core_web_sm')
doc = nlp('This is a test.')
print('✅ spaCy English model available')
" 2>/dev/null; then
        echo "✅ spaCy English model verification passed"
    else
        echo "⚠️  spaCy English model verification failed"
    fi
    
    # Test spaCy Chinese model (optional)
    if python3 -c "
import spacy
nlp = spacy.load('zh_core_web_sm')
doc = nlp('这是测试。')
print('✅ spaCy Chinese model available')
" 2>/dev/null; then
        echo "✅ spaCy Chinese model verification passed"
    else
        echo "⚠️  spaCy Chinese model not available (optional)"
    fi
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verify   Only verify existing installations"
    echo "  --no-venv      Skip virtual environment activation"
    echo
    echo "This script downloads required NLP data for AIECS ClassifierTool:"
    echo "  - NLTK stopwords corpus"
    echo "  - spaCy English model (en_core_web_sm)"
    echo "  - spaCy Chinese model (zh_core_web_sm, optional)"
    echo
}

# Parse command line arguments
VERIFY_ONLY=false
SKIP_VENV=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -v|--verify)
            VERIFY_ONLY=true
            shift
            ;;
        --no-venv)
            SKIP_VENV=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo "📍 Project root: $PROJECT_ROOT"
    echo
    
    # Activate virtual environment if available and not skipped
    if [[ "$SKIP_VENV" != true ]]; then
        activate_venv || true
    fi
    
    # Check dependencies
    check_dependencies
    
    if [[ "$VERIFY_ONLY" == true ]]; then
        echo
        echo "🔍 Running verification only..."
        verify_installation
    else
        # Download NLP data
        if run_download_script; then
            verify_installation
            echo
            echo "🎉 NLP data setup completed successfully!"
            echo "AIECS ClassifierTool is ready to use."
        else
            echo
            echo "❌ NLP data setup failed. Please check the errors above."
            exit 1
        fi
    fi
    
    echo
    echo "=================================================="
    echo "Setup complete!"
    echo "=================================================="
}

# Run main function
main "$@"
