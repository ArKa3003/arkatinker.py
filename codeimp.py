#!/bin/bash


set -e  # Exit on error

# Configuration variables
SOFTWARE_DIR="$HOME/software"
TINKER_DIR="$SOFTWARE_DIR/tinker"
LOG_FILE="$SOFTWARE_DIR/build_log.txt"
MINICONDA_INSTALLER="Miniconda3-latest-MacOSX-x86_64.sh"
PSI4_ENV_NAME="psi4env"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Function to log warnings
warn() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1" >> "$LOG_FILE"
}

# Function to log errors
error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" >> "$LOG_FILE"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Create directory structure
setup_directories() {
    log "Setting up directory structure"
    mkdir -p "$SOFTWARE_DIR"
    touch "$LOG_FILE"
}

# Check and install prerequisites
check_prerequisites() {
    log "Checking prerequisites"
    
    # Check for Xcode Command Line Tools
    if ! command_exists xcode-select; then
        warn "Xcode Command Line Tools not found. Installing..."
        xcode-select --install
        warn "After Xcode Command Line Tools installation completes, please run this script again."
        exit 0
    fi
    
    # Check for required compilers
    if ! command_exists gcc || ! command_exists gfortran; then
        warn "GCC and/or gfortran not found. Installing via Homebrew..."
        
        # Check for Homebrew
        if ! command_exists brew; then
            log "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        
        log "Installing GCC (includes gfortran)..."
        brew install gcc
    fi
    
    # Check for git
    if ! command_exists git; then
        log "Installing Git..."
        brew install git
    fi
}

# Part 1: Build Tinker from source
build_tinker() {
    log "Starting Tinker build process"
    
    # Clone Tinker repository if it doesn't exist
    if [ ! -d "$TINKER_DIR" ]; then
        log "Cloning Tinker repository"
        cd "$SOFTWARE_DIR"
        git clone https://github.com/TinkerTools/Tinker.git tinker
    else
        log "Tinker repository already exists, updating"
        cd "$TINKER_DIR"
        git pull
    fi
    
    # Build FFTW
    log "Building FFTW library"
    cd "$TINKER_DIR/fftw"
    
    # Set compiler environment variables
    export CC=gcc
    export F77=gfortran
    
    # Clean any previous builds
    make distclean || true
    
    # Configure FFTW with thread support and OpenMP
    ./configure --prefix="$(pwd)" --enable-threads --enable-openmp
    
    # Build and install FFTW
    make
    make install
    
    # Check if FFTW libraries were built successfully
    if [ ! -f "$TINKER_DIR/fftw/lib/libfftw3.a" ] || [ ! -f "$TINKER_DIR/fftw/lib/libfftw3_threads.a" ]; then
        error "FFTW libraries were not built successfully. Check the log for details."
        exit 1
    fi
    
    # Prepare Makefile for compiling Tinker
    log "Preparing Makefile for Tinker compilation"
    cd "$TINKER_DIR/source"
    
    # Copy the Makefile from make directory
    cp "../make/Makefile" .
    
    # Backup the original Makefile
    cp Makefile Makefile.backup
    
    # Update BUILDDIR in the Makefile to point to the correct directory
    log "Modifying Makefile paths"
    ABSOLUTE_TINKER_PATH=$(cd "$TINKER_DIR" && pwd)
    sed -i '' "s|BUILDDIR = \$(HOME)/ffe/build|BUILDDIR = $ABSOLUTE_TINKER_PATH|" Makefile
    
    # Create bin directory if it doesn't exist
    mkdir -p "$TINKER_DIR/bin"
    
    # Build Tinker
    log "Building Tinker (this may take a while)"
    make all
    
    # Install Tinker executables
    log "Installing Tinker executables"
    make install
    
    log "Tinker has been built successfully!"
    
    # Testing Tinker installation
    log "Testing Tinker installation"
    cd "$TINKER_DIR/bin"
    if [ -f "./analyze" ]; then
        log "Tinker installation verified: analyze executable exists"
    else
        error "Tinker installation failed: analyze executable not found"
        exit 1
    fi
}

# Part 2: Install psi4 through conda
install_psi4() {
    log "Starting psi4 installation process"
    
    # Check if conda is already installed
    if ! command_exists conda; then
        log "Installing Miniconda"
        cd "$SOFTWARE_DIR"
        # Download Miniconda installer
        curl -O "https://repo.anaconda.com/miniconda/$MINICONDA_INSTALLER"
        
        # Install Miniconda silently
        bash "$MINICONDA_INSTALLER" -b -p "$SOFTWARE_DIR/miniconda3"
        
        # Add conda to the PATH
        export PATH="$SOFTWARE_DIR/miniconda3/bin:$PATH"
        
        # Initialize conda for bash
        "$SOFTWARE_DIR/miniconda3/bin/conda" init bash
        
        # Source the bash profile to use conda immediately
        source "$HOME/.bash_profile" || source "$HOME/.bashrc" || source "$HOME/.zshrc" || true
        
        log "Miniconda installed. You may need to restart your terminal or run 'source ~/.bash_profile' to use conda."
    else
        log "Conda is already installed"
    fi
    
    # Ensure conda command is available in this script
    export PATH="$SOFTWARE_DIR/miniconda3/bin:$PATH"
    
    # Check if the psi4 environment already exists
    if conda env list | grep -q "$PSI4_ENV_NAME"; then
        warn "psi4 environment '$PSI4_ENV_NAME' already exists. Skipping creation."
    else
        # Create a new conda environment for psi4
        log "Creating conda environment for psi4"
        conda create -y -n "$PSI4_ENV_NAME" python=3.9
    fi
    
    # Install psi4
    log "Adding necessary conda channels"
    conda config --add channels conda-forge
    conda config --add channels psi4
    
    log "Installing psi4 in the '$PSI4_ENV_NAME' environment"
    conda install -y -n "$PSI4_ENV_NAME" psi4 psi4-rt
    
    log "psi4 has been installed successfully!"
    
    # Test psi4 installation
    log "Testing psi4 installation"
    # Create a simple test input file
    TEST_DIR="$SOFTWARE_DIR/psi4_test"
    mkdir -p "$TEST_DIR"
    
    cat > "$TEST_DIR/test.inp" << EOF
molecule {
0 1
H
H 1 0.9
}

set basis sto-3g
energy("scf")
EOF
    
    # Run psi4 on the test input
    log "Running psi4 test calculation"
    cd "$TEST_DIR"
    
    # Need to activate the conda environment first
    eval "$(conda shell.bash hook)"
    conda activate "$PSI4_ENV_NAME"
    
    if psi4 --version &> /dev/null; then
        log "psi4 installation verified: psi4 command works"
        log "Running a simple psi4 calculation (H2 molecule)..."
        psi4 test.inp > test.out 2>&1
        
        if grep -q "Hartree" test.out; then
            log "psi4 calculation completed successfully!"
        else
            warn "psi4 calculation may have issues. Check $TEST_DIR/test.out for details."
        fi
    else
        error "psi4 installation issues: psi4 command not found or not working"
    fi
}

# Main execution
main() {
    setup_directories
    check_prerequisites
    
    log "Starting build and installation process for Tinker and psi4"
    
    # Build Tinker
    build_tinker
    
    # Install psi4
    install_psi4
    
    log "Build and installation process completed successfully!"
    log "Tinker executables are in: $TINKER_DIR/bin"
    log "psi4 is installed in the '$PSI4_ENV_NAME' conda environment"
    log "To use psi4, run: conda activate $PSI4_ENV_NAME"
    log "For detailed information, check the log file: $LOG_FILE"
}

# Run the main function
main
