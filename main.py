from tqdm import tqdm
from mem import MemorySystem
# pylint: disable=redefined-outer-name


def parse_din(file_path: str) -> list[dict]:
    with open(file_path, 'r') as f:
        return [(int((d := i.split(' '))[0]), int(d[1], 16)) for i in f.readlines()]


def run_test(tracefile: str, associativity=4, progress_bar=True):
    data = parse_din(tracefile)
    memory_system = MemorySystem(associativity=associativity)
    for i in (tqdm(data) if progress_bar else data):
        memory_system.access(*i)
    return memory_system

if __name__ == '__main__':
    run_test("Traces/Spec_Benchmark/008.espresso.din")
