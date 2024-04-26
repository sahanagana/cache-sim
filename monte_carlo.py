from pathlib import Path
import os
import shutil
import math
import multiprocessing as mp
import numpy as np
from tqdm import tqdm
from cache_sim import parse_din, output_to_din, run_test


class MonteCarloGenerator:
    CACHE_LINE_SIZE = 64

    def __init__(self,
                 trace_dir: str,
                 outdir: str,
                 workload_len: int,
                 splice_prob: float,
                 mut_prob: float,
                 random_seed=None):
        print("Loading data...")
        self.trace_files = [
            np.array(parse_din(Path(trace_dir) / i))
            for i in os.listdir(trace_dir)
        ]
        max_addr = np.max(np.concatenate(self.trace_files, axis=0).T[1])
        self.addr_size = math.ceil(math.log2(max_addr))
        self.workload_len = workload_len
        self.splice_prob = splice_prob
        self.mut_prob = mut_prob
        self.rng = np.random.default_rng(seed=random_seed)
        self.outdir = Path(outdir)

    def geometric_generator(self, maximum, p):
        i = self.rng.geometric(p)
        total = i
        while total < maximum:
            yield i
            i = self.rng.geometric(p)
            total += i
        yield maximum - (total - i)

    def random_splice(self, length: int):
        workload = self.trace_files[self.rng.integers(len(self.trace_files))]
        start = self.rng.integers(len(workload))
        end = start + length
        overlap = end - len(workload) if end - len(workload) > 0 else 0
        return np.concatenate([workload[start:end], workload[:overlap]])

    def gen_workload(self):
        traces = np.concatenate([
            self.random_splice(i) for i in self.geometric_generator(
                self.workload_len, self.splice_prob)
        ],
                                axis=0)

        # Mutate access types
        acc_type_mut_ind = self.rng.uniform(size=len(traces)) < self.mut_prob
        traces[acc_type_mut_ind,
               0] = self.rng.integers(0, 3, size=np.sum(acc_type_mut_ind))

        # Mutate address being accessed
        max_addr = 2**self.addr_size
        addr_mut_ind = self.rng.uniform(size=len(traces)) < self.mut_prob
        # Add a normally distributed value to somewhat preserve locality of reference
        addr_to_add = self.rng.normal(  # STD: CACHE_LINE_SIZE
            scale=max_addr *
            2**-(self.addr_size - math.log2(self.CACHE_LINE_SIZE)),
            size=np.sum(addr_mut_ind)).astype(traces.dtype)  # Cast to int
        # Complicated way of saying, max should be max_addr and min should be -max_addr
        addr_to_add = np.where(
            addr_to_add < max_addr, addr_to_add,
            np.where(addr_to_add > 0, np.full_like(addr_to_add, max_addr),
                     np.full_like(addr_to_add, -max_addr)))
        addr_to_add[addr_to_add <
                    0] += max_addr  # Flip negatives into positives after mod
        traces[addr_mut_ind,
               1] = (traces[addr_mut_ind, 1] + addr_to_add) % max_addr
        return traces

    def prep_sim(self):
        print("Generating Monte Carlo simulations...")
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        os.mkdir(self.outdir)

    def gen_case(self, l1_size: int, l2_size: int, prefix=''):
        prefix = str(prefix) + '_' if str(prefix) else ''
        output_to_din(self.outdir / f"{prefix}{l1_size}_{l2_size}.din",
                      self.gen_workload())

    def _gen_case_star(self, args):
        self.gen_case(*args)

    def varying_cache_sizes(self, min_l1, max_l1, step_l1, min_l2, max_l2,
                            step_l2):
        self.prep_sim()
        for i in tqdm(range(min_l1, max_l1, step_l1)):
            for j in range(min_l2, max_l2, step_l2):
                self.gen_case(i, j)

    def fixed_workloads_random_caches(self,
                                      num_workloads: int,
                                      l1: tuple,
                                      l2: tuple,
                                      jobs=1,
                                      chunksize=1):
        self.prep_sim()
        l1_size = self.rng.choice(np.arange(*l1), num_workloads)
        l2_size = self.rng.choice(np.arange(*l2), num_workloads)
        with mp.Pool(jobs) as p:
            list(
                tqdm(p.imap_unordered(self._gen_case_star,
                                      zip(l1_size, l2_size,
                                          range(num_workloads)),
                                      chunksize=chunksize),
                     total=num_workloads))


class SimulationRunner:

    def __init__(self,
                 simdir: str,
                 outdir: str,
                 jobs=1,
                 chunksize=1,
                 random_seed=None):
        self.trace_files = []
        seed_sequence = np.random.SeedSequence(random_seed).generate_state(
            len(os.listdir(simdir)))
        for i, seed in zip(os.listdir(simdir), seed_sequence):
            parts = i.split('.')[0].split('_')
            kwargs = {'l1_size': int(parts[1]), 'l2_size': int(parts[2])}
            self.trace_files.append((Path(simdir) / i, kwargs, seed))
        self.jobs = jobs
        self.chunksize = chunksize
        self.outdir = Path(outdir)

    def single_test(self, args: tuple[str, dict, int]):
        sim_out = run_test(args[0],
                           **args[1],
                           progress_bar=False,
                           random_seed=args[2])
        energy = np.cumsum(np.sum(sim_out.report('Energy'), axis=0))
        with open((self.outdir / args[0].stem).with_suffix('.csv'), 'w') as f:
            f.write('\n'.join(energy.astype(str)))

    def run(self):
        print("Running simulations...")
        if os.path.exists(self.outdir):
            shutil.rmtree(self.outdir)
        os.mkdir(self.outdir)
        with mp.Pool(self.jobs) as p:
            list(
                tqdm(p.imap_unordered(self.single_test,
                                      self.trace_files,
                                      chunksize=self.chunksize),
                     total=len(self.trace_files)))


def gen_monte_carlo():
    l1_params = 2**8, 2**18, 2**14
    l2_params = 2**11, 2**21, 2**14
    wc_l = 2**12
    wc_c = 2**14
    mg = MonteCarloGenerator('Traces/Spec_Benchmark/',
                             'monte_carlo_tests',
                             wc_l,
                             1 / 2**7,
                             1 / 2**5,
                             random_seed=0)
    mg.fixed_workloads_random_caches(wc_c,
                                     l1_params,
                                     l2_params,
                                     jobs=12,
                                     chunksize=16)


def run_monte_carlo():
    sr = SimulationRunner('monte_carlo_tests', 'mc_out', jobs=4, chunksize=1)
    sr.run()


if __name__ == '__main__':
    gen_monte_carlo()
    run_monte_carlo()
