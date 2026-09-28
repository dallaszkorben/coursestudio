#!/bin/bash
# Virtual environment activation helper script
# Usage: source activate_venv.sh

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Activating CourseStudio Virtual Environment${NC}"
echo -e "${BLUE}================================================${NC}"
echo

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

echo -e "${GREEN}✅ Virtual environment activated${NC}"
echo "Location: $SCRIPT_DIR/venv"
echo "Python:   $(python --version)"
echo "Pip:      $(pip --version)"
echo

echo -e "${BLUE}Available commands:${NC}"
echo "  python src/main.py          - Run application"
echo "  pytest tests/                - Run tests"
echo "  python src/main.py --help   - Show help"
echo "  deactivate                   - Deactivate venv"
echo

echo -e "${GREEN}Ready to develop! 🚀${NC}"
echo
