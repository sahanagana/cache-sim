from tqdm import tqdm
import numpy as np
from mem import MemorySystem
# pylint: disable=redefined-outer-name


def parse_din(file_path: str) -> list[dict]:
    with open(file_path, 'r') as f:
        return [(int((d := i.split(' '))[0]), int(d[1], 16)) for i in f.readlines()]


def output_to_din(file_path: str, traces: list[list[int, int]]):
    traces = [' '.join([hex(j)[2:] for j in i]) for i in traces]
    with open(file_path, 'w') as f:
        f.write('\n'.join(traces))


def run_test(tracefile: str, progress_bar=True, **kwargs):
    data = parse_din(tracefile)
    memory_system = MemorySystem(**kwargs)
    for i in (tqdm(data) if progress_bar else data):
        memory_system.access(*i)
    return memory_system

if __name__ == '__main__':
    result = run_test("Traces/Spec_Benchmark/008.espresso.din")
    print(np.array(result.report('Energy')).shape)
