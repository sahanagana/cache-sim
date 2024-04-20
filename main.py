from tqdm import tqdm
from mem import L1Cache
# pylint: disable=redefined-outer-name


def parse_din(file_path: str) -> list[dict]:
    print("Parsing input file...")
    with open(file_path, 'r') as f:
        return [(int((d := i.split(' '))[0]), int(d[1], 16)) for i in tqdm(f.readlines())]

if __name__ == '__main__':
    tracefile = "Traces/Spec_Benchmark/008.espresso.din"
    data = parse_din(tracefile)
    memory_system = L1Cache()
    print("Running simulation...")
    results = [memory_system.access(*i) for i in tqdm(data)]
    memory_system.report()
