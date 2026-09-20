# mangpx Installation & Setup Guide

**Last Updated:** 2026-09-20  
**Python Version Required:** 3.10+  
**Platform:** Linux/Mac/Windows

---

## Quick Start (5 minutes)

### 1. Navigate to project directory
```bash
cd /home/akoel/Projects/boat/general/Code/mangpx
```

### 2. Activate virtual environment
```bash
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Or use the helper script (Linux/Mac):
source activate_venv.sh
```

### 3. Verify installation
```bash
python tests/test_app_config.py
```

**Expected result:** ✅ All AppConfig tests PASSED (25/25)

### 4. Run the application
```bash
python src/main.py
```

---

## Detailed Installation

### Prerequisites
- Python 3.10 or later
- pip package manager
- git (optional, for version control)

### Step 1: Create Virtual Environment

```bash
cd /home/akoel/Projects/boat/general/Code/mangpx
python3 -m venv venv
```

**Output:**
```
✅ Virtual environment created
```

### Step 2: Activate Virtual Environment

**Linux/Mac:**
```bash
source venv/bin/activate
```

**Windows (Command Prompt):**
```bash
venv\Scripts\activate
```

**Windows (PowerShell):**
```bash
venv\Scripts\Activate.ps1
```

**Expected prompt change:**
```
(venv) $ 
```

### Step 3: Upgrade pip

```bash
pip install --upgrade pip setuptools wheel
```

### Step 4: Install Project Dependencies

```bash
pip install -r requirements.txt
```

**Expected result:**
```
Successfully installed PyQt5-5.15.7 PyQtWebEngine-5.15.7 gpxpy-1.6.2 lxml-4.9.3 pytest-7.4.3 pytest-timeout-2.1.0
```

### Step 5: Verify Installation

```bash
python << 'EOF'
import PyQt5
import gpxpy
import pytest
print("✅ All core dependencies installed successfully")
EOF
```

---

## Installed Dependencies

### Core GUI
- **PyQt5 5.15.7** - GUI framework
- **PyQtWebEngine 5.15.7** - Web rendering for maps

### Data Processing
- **gpxpy 1.6.2** - GPX file parsing and manipulation
- **lxml 4.9.3** - XML processing (required by gpxpy)

### Standard Library (Built-in)
- **sqlite3** - Database access (for mbtiles)
- **configparser** - Configuration file handling
- **json** - JSON data handling
- **math** - Mathematical functions (Haversine formula)
- **re** - Regular expressions

### Testing
- **pytest 7.4.3** - Unit testing framework
- **pytest-timeout 2.1.0** - Timeout plugin for tests

---

## Verification Checklist

After installation, verify everything is working:

```bash
# Check Python version
python --version
# Expected: Python 3.10+ or 3.12+

# Check virtual environment
which python  # (or 'where python' on Windows)
# Should show path to venv/bin/python

# Run unit tests
pytest tests/test_app_config.py -v
# Expected: 25 passed

# Run application (will show window briefly)
timeout 3 python src/main.py || true
# Expected: Application initializes without errors
```

---

## Troubleshooting

### Issue: "python: command not found"
**Solution:** Use `python3` instead of `python`
```bash
python3 -m venv venv
```

### Issue: Virtual environment not activating
**Solution:** Check file path and use full path
```bash
# On Linux/Mac, try:
source ./venv/bin/activate

# Or absolute path:
source /home/akoel/Projects/boat/general/Code/mangpx/venv/bin/activate
```

### Issue: "ModuleNotFoundError: No module named 'PyQt5'"
**Solution:** Ensure virtual environment is activated and dependencies installed
```bash
source venv/bin/activate  # Activate venv
pip install -r requirements.txt  # Install dependencies
```

### Issue: PyQt5 installation fails
**Solution:** May need system libraries on Linux
```bash
# Ubuntu/Debian:
sudo apt-get install python3-pyqt5

# Or reinstall:
pip install --force-reinstall PyQt5==5.15.7
```

### Issue: Tests fail with timeout
**Solution:** Increase timeout or check for infinite loops
```bash
pytest tests/ --timeout=60
```

### Issue: "Permission denied" on activate_venv.sh
**Solution:** Make script executable
```bash
chmod +x activate_venv.sh
```

---

## Development Workflow

### Daily Development

```bash
# 1. Open terminal and navigate to project
cd /home/akoel/Projects/boat/general/Code/mangpx

# 2. Activate virtual environment
source venv/bin/activate
# or use helper: source activate_venv.sh

# 3. Run application
python src/main.py

# 4. Run tests (in another terminal with venv activated)
pytest tests/

# 5. When done, deactivate
deactivate
```

### Adding New Dependencies

If you need to add a new library:

```bash
# 1. Install with pip
pip install package_name

# 2. Update requirements.txt
pip freeze > requirements.txt

# 3. Document in requirements.txt with version pin:
# package_name==1.2.3  # Description
```

### Recreating Virtual Environment

If virtual environment gets corrupted:

```bash
# 1. Remove old venv
rm -rf venv

# 2. Create new one
python3 -m venv venv

# 3. Activate
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Verify
python tests/test_app_config.py
```

---

## File Locations Reference

```
/home/akoel/Projects/boat/general/Code/mangpx/
├── venv/                          ← Virtual environment
├── requirements.txt               ← Dependency list
├── activate_venv.sh              ← Activation helper (Linux/Mac)
├── src/
│   ├── main.py                   ← Application entry point
│   └── ... (other modules)
├── config/
│   ├── settings.ini              ← User configuration
│   ├── app_config.py            ← Configuration loader
│   └── constants.py             ← Application constants
├── tests/
│   └── test_app_config.py        ← Unit tests
└── doc/
    └── (documentation)
```

---

## Command Reference

### Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Deactivate (all platforms)
deactivate
```

### Package Management

```bash
# Install from requirements
pip install -r requirements.txt

# Install single package
pip install package_name==version

# List installed packages
pip list

# Update pip
pip install --upgrade pip

# Uninstall package
pip uninstall package_name
```

### Application

```bash
# Run application
python src/main.py

# Run with debug output
python src/main.py --debug

# Open specific file
python src/main.py --file track.gpx

# Show help
python src/main.py --help
```

### Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_app_config.py

# Run with verbose output
pytest tests/ -v

# Run with timeout (seconds)
pytest tests/ --timeout=30

# Show test coverage
pytest tests/ --cov=src
```

---

## System Requirements

### Minimum
- **RAM:** 512 MB
- **Disk:** 500 MB (including dependencies)
- **Python:** 3.10+

### Recommended
- **RAM:** 2 GB
- **Disk:** 1 GB
- **Python:** 3.11 or 3.12

### Supported Operating Systems
- ✅ Linux (Ubuntu, Debian, Fedora, etc.)
- ✅ macOS (Intel and Apple Silicon)
- ✅ Windows 10/11

---

## Getting Help

If you encounter issues:

1. **Check this file:** INSTALLATION.md (Troubleshooting section)
2. **Check project docs:** doc/README.md (Documentation index)
3. **Review logs:** Check terminal output for error messages
4. **Review code:** Search in src/ for similar implementations

---

## Next Steps After Installation

1. ✅ Virtual environment created and activated
2. ✅ Dependencies installed and verified
3. ✅ Unit tests passing (25/25 ✅)
4. **→ Ready to develop!**

For development instructions, see: `doc/README.md`

---

**Last Updated:** 2026-09-20  
**Installation Time:** ~5-10 minutes  
**All Systems:** Linux, macOS, Windows
