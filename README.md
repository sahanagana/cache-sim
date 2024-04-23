# Energy-Performance Tradeoffs of Memory Sytems Project

This file contains instructions on how to run our code, as well as a general file overview.

`run.sh` - Main run file. Checks if your python verion is correct (3.10), sets up virtual environment, and installs all needed dependencies, then runs the simulator on all the trace files, outputting data points such as energy consumption and time for the different components. Run with `bash run.sh`

`Traces` - Directory containing traces in dinero format. Our simulator uses these traces to run.

`mem.py` - Python file that contains L1, L2, and DRAM classes along with methods to simulate accesses, hits, misses, etc.

`main.py` - Python file that contains methods for parsing in dinero traces and setting specifications such as associativity.

`simtest.py` - Python driver code that runs the simulator on all of the traces in the `Traces` directory and prints results.

`report.md` - Report containing our design choices, tables for data points of each component and each trace file, and our conclusion on the effect of L2 cache associativity on energy consumption.

