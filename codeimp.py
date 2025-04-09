#!/bin/bash
# Complete end-to-end script for building Tinker from source and installing Psi4 through conda

# Exit on error
set -e

# Set installation directory
INSTALL_DIR="$HOME/computational_chemistry"
mkdir -p $INSTALL_DIR
cd $INSTALL_DIR

echo "=== Building Tinker from source ==="

# Install prerequisites (uncomment as needed for your system)
# Ubuntu/Debian:
# sudo apt-get update
# sudo apt-get install -y build-essential gfortran git libfftw3-dev

# CentOS/RHEL:
# sudo yum install -y gcc gcc-gfortran make git fftw-devel

# macOS (with Homebrew):
# brew install gcc fftw git

# Clone Tinker repository
git clone https://github.com/TinkerTools/Tinker.git
cd Tinker

# Set Tinker home directory
TINKER_HOME="$INSTALL_DIR/Tinker"

# Prepare build environment - using gfortran
cp make/Makefile.gfortran source/Makefile
cd source

# Modify Makefile to set correct paths
# This uses sed to replace the TINKERDIR line
sed -i'.bak' "s|TINKERDIR = .*|TINKERDIR = $TINKER_HOME|" Makefile

# Build Tinker
make all -j4

# Create bin directory and copy executables
cd ..
mkdir -p bin
cp source/analyze source/dynamic source/minimize source/testgrad source/testhess \
   source/testrot source/timer source/timerot source/bar source/pdbxyz source/xyzpdb \
   source/spacefill source/spectrum source/superpose source/correlate source/crystal \
   source/diffuse source/distgeom source/document source/scan source/xtalfit \
   source/xtalmin source/xyzedit source/xyzint source/xyzmol2 source/xyzpdb bin/

# Set up environment variables
echo "export TINKER_HOME=\"$TINKER_HOME\"" >> ~/.bashrc
echo "export PATH=\"\$TINKER_HOME/bin:\$PATH\"" >> ~/.bashrc
source ~/.bashrc

# Verify Tinker installation
echo "Verifying Tinker installation..."
which analyze
which dynamic

cd $INSTALL_DIR

echo "=== Installing Psi4 through conda ==="

# Install Miniconda if not already installed
if [ ! -d "$HOME/miniconda3" ]; then
  echo "Installing Miniconda..."
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -O miniconda.sh
  else
    echo "Unsupported operating system"
    exit 1
  fi
  
  bash miniconda.sh -b -p $HOME/miniconda3
  rm miniconda.sh
fi

# Initialize conda for bash shell
eval "$($HOME/miniconda3/bin/conda shell.bash hook)"

# Create conda environment for Psi4
conda create -n psi4env python=3.9 -y

# Activate environment and install Psi4
conda activate psi4env
conda config --add channels conda-forge
conda config --add channels psi4
conda install psi4 psi4-rt -c psi4 -y

# Create a test script for Psi4
mkdir -p $INSTALL_DIR/psi4_test
cat > $INSTALL_DIR/psi4_test/water.py << 'EOF'
import psi4

# Set memory and output file
psi4.set_memory('2 GB')
psi4.set_output_file('water_energy.dat')

# Define the water molecule
water = psi4.geometry("""
O
H 1 0.96
H 1 0.96 2 104.5
""")

# Set the computational method and basis set
psi4.set_options({'basis': '6-31g'})

# Compute the energy
energy = psi4.energy('scf')

# Print the result
print(f"SCF energy: {energy}")
EOF

# Verify Psi4 installation
echo "Verifying Psi4 installation..."
cd $INSTALL_DIR/psi4_test
conda activate psi4env
python -c "import psi4; print(f'Psi4 version: {psi4.__version__}')"
python water.py

echo "=== Installation Complete ==="
echo "Tinker is installed at: $TINKER_HOME"
echo "Psi4 is installed in conda environment: psi4env"
echo ""
echo "To use Tinker: source ~/.bashrc"
echo "To use Psi4: conda activate psi4env"
