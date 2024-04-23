# Plan

- Make run.sh:
    * Automatically check for correct Python version/throw error if wrong
    * Create virtual Python environment
    * Install all dependencies (matplotlib, tqdm, numpy)
    * Run simtest.py (for all traces)
    * Arguments: number of trials, (optional) number of jobs
- Adjust simtest.py:
    * Change what we print for each test (mean + std over num_trials):
        + Total time to process each request (we have this)
        + Total energy for the test (we have this)
        + For each component (L1 instr/L1 data/L2/DRAM):
            + # accesses (done)
            + # misses (done)
            + Total energy consumed by component (done)
        + Repeat for 2/4/8 associativity
    * OPTIONAL: multiprocessing for simtest.py
        + To speed up run times. Modify run.sh to take jobs as argument.
- Make report:
    * All design decisions we made (located above the table)
    * Result for each trace file, organized as a sequence of tables
        + Mean + standard deviation for all number (optional but recommended)
    * Comment on how L2 set associativity affects the system from the above tables (our conclusions/opinions/hot takes)
