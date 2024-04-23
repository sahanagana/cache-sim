# Energy-Performance Tradeoffs of Memory Sytems Project

This file contains instructions on how to run our code, as well as a general file overview.

`run.sh` - Main run file. Checks if Python is installed, sets up virtual environment, and installs all needed dependencies, then runs the simulator on all the trace files, outputting data points such as energy consumption and time for the different components. Run with `bash run.sh` Arguments: path_to_tests_dir, num_trials. The path to the tests directory is generally Traces/Spec_Benchmark.

`Traces` - Directory containing traces in dinero format. Our simulator uses these traces to run.

`mem.py` - Python file that contains MemorySystem, L1, L2, and DRAM classes along with methods to simulate accesses, hits, misses, etc.

`main.py` - Python file that contains methods for parsing in dinero traces and calls the MemorySystem on every input in a given trace file.

`simtest.py` - Test script that runs the simulator on all of the traces in the given directory and prints results, as well as outputs to the file `py_out.txt`.

`report.md` - Report containing our design choices, tables for data points of each component and each trace file, and our conclusion on the effect of L2 cache associativity on energy consumption.
