import os
import argparse
from functools import reduce
from tqdm import tqdm
import pandas as pd
from main import run_test


class Tester:
    def __init__(self, name: str, trials: int):
        self.name, self.trials = name, trials
        self.levels = ['L1 ICache', 'L1 DCache', 'L2 Cache', 'DRAM']
        self.stats = ['Accesses', 'Misses', 'Energy', 'Time']

    def run_test(self, associativity=4):
        results = run_test(self.name, associativity, False)
        return reduce(lambda a, b: a | b, [self._get_stat(results, i) for i in self.stats], {})

    def run_trials(self, associativity=4):
        result = pd.DataFrame([self.run_test(associativity) for _ in tqdm(range(self.trials))])
        for i in ['Energy', 'Time']:
            result[f'Total {i}'] = result[[f"{j} {i}" for j in self.levels]].sum(axis=1)
        return result

    def test_associativities(self, to_try=None):
        to_try = to_try if to_try is not None else [2, 4, 8]
        print(f"Trying associativities: {', '.join(str(i) for i in to_try)} with {self.trials} \
              trials each.")
        return [(i, self.run_trials(associativity=i)) for i in to_try]

    def dump_associativity_test(self, data):
        buf = f"Testing {self.name} with {self.trials} trials..."
        for i in data:
            summary = pd.DataFrame({
                'Mean': i[1].mean(),
                'Standard Deviation': i[1].std(),
            }).T
            buf = f"{buf}\n\nAssociativity {i[0]}:\n{i[1].to_string()}\nSummary:\n" + \
                f"{summary.to_string()}"
        return buf

    @staticmethod
    def _merge_fn(a, b):
        return a | b

    def _get_stat(self, results: list, stat: str) -> dict:
        res = results.report(stat)
        return {f"{self.levels[j]} {stat}": sum(res[j]) for j in range(len(self.levels))}


def dinero_test(name: str, trials: int, outfile=None, to_try=None):
    t = Tester(name, trials)
    results = t.test_associativities(to_try=to_try)
    results_str = t.dump_associativity_test(results)
    print(results_str)
    if outfile:
        with open(outfile, 'w') as f:
            f.write(results_str)
    return results_str


def all_dinero(trials: int, outfile=None, to_try=None):
    buf = ''
    for i in os.listdir("Traces/Spec_Benchmark"):
        buf += dinero_test(os.path.join("Traces/Spec_Benchmark", i), trials, to_try=to_try)
        print('-' * 80)
        buf += '-' * 80
    if outfile:
        with open(outfile, 'w') as f:
            f.write(buf)
    return buf


if __name__ == '__main__':
    #dinero_test('Traces/Spec_Benchmark/008.espresso.din', 3, 'py_out.txt')
    all_dinero(8)
