#!/bin/bash


echo "Please be sure Python >=3.10 is installed and appropriately aliased prior to running this script!"

python_cmd=""

# check if python installed
if  command -v python3 ; then
    python_version=$(python3 -V 2>&1)
    python_cmd="python3"
elif  command -v python ; then
    python_version=$(python -V 2>&1)
    python_cmd="python"
else
    echo "Python is required for to run our simulator. Please install before proceeding."
    exit 1
fi

# Output the version and check if it is the correct version
echo "Python version: $python_version"

# Create Python virtual environment
if  ! test -d venv; then
    $python_cmd -m venv venv

    # install dependencies
    $python_cmd -m pip install pandas tqdm
fi
python_cmd="venv/bin/python"

# run simtest for all traces
$python_cmd simtest.py $1 $2

