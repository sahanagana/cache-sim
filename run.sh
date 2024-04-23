#!/bin/bash

required_version="3.10"
num_trials="$1"

# Function to check if a command is available
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# check if version is correct 
if command_exists python3; then
    echo "Python 3 found."
    python_version=$(python3 -V 2>&1)
else
    echo "Python 3 is required for to run our simulator."
    exit 1
fi

# Output the version and check if it is the correct version
echo "Python version: $python_version"

if [[ ! "$python_version" == *"$required_version"* ]]; then
    echo "Required Python version is $required_version, found version: $python_version"
    exit 1
fi

# install dependencies
python3 -m pip install --user matplotlib numpy tqdm

# Create Python virtual environment and run simtest for all traces
python3 -m venv venv
python3 simtest.py $num_trials

