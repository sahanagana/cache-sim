from tqdm import tqdm
from mem import L1Cache
# pylint: disable=redefined-outer-name


def parse_din(file_path: str) -> list[dict]:
    print("Parsing input file...")
    with open(file_path, 'r') as f:
        return [(int((d := i.split(' '))[0]), int(d[1], 16)) for i in f.readlines()]


def run_test(tracefile: str, associativity=4):
    data = parse_din(tracefile)
    memory_system = L1Cache(associativity=associativity)
    print("Running simulation...")
    results = [memory_system.access(*i) for i in tqdm(data)]
    memory_system.report()
    print(f'Total time taken: {sum(i.energy for i in results)}')
    return memory_system

if __name__ == '__main__':
    run_test("Traces/Spec_Benchmark/008.espresso.din")
