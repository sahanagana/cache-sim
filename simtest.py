import matplotlib.pyplot as plt
import numpy as np
from main import run_test


def output_tests(cases, outfile):
    with open(outfile, 'w') as f:
        cases = [' '.join(i) for i in cases]
        f.write('\n'.join(cases))

def plot_misses(memory_system, level='l1', title=''):
    if level == 'l2':
        memory_system = memory_system.next
    elif level == 'dram':
        memory_system = memory_system.next.next
    y = np.cumsum(memory_system.stats['misses'])
    plt.plot(y)
    plt.xlabel('Instruction #')
    plt.ylabel(f"{level.capitalize()} Cumulative Miss Count")
    plt.title(title)
    plt.savefig(f'{title or "out"}.png')
    plt.close('all')


def l1_test():
    print("Testing L1 Cache...")
    cases = [('0', hex((i * 64) % (256 * 64))[2:]) for i in range(2 ** 12)]
    output_tests(cases, 'test.din')
    plot_misses(run_test('test.din'), title='L1 Cache Test')


def l1_thrash():
    print("Testing L1 Cache (Thrashing)...")
    cases = [('0', hex((i * 64) % (256 * 64 + 1))[2:]) for i in range(2 ** 14)]
    output_tests(cases, 'test.din')
    plot_misses(run_test('test.din'), 'l2', title='L1_L2 Thrashing Cache Test')


def l2_test():
    print("Testing L2 Cache...")
    cases = [('0', hex((i * 64) % (128 * 1024))[2:]) for i in range(2 ** 14)]
    output_tests(cases, 'test.din')
    plot_misses(run_test('test.din'), 'l2', title='L2 Cache Test')


def l1_write_test():
    print("Testing L1 Cache (Write)...")
    cases = [('1', hex((i * 64) % (256 * 64))[2:]) for i in range(2 ** 12)]
    output_tests(cases, 'test.din')
    plot_misses(run_test('test.din'), title='L1 Cache Write Test')


def dinero_test():
    print("Running on real Dinero trace...")
    plot_misses(run_test("Traces/Spec_Benchmark/008.espresso.din"), 'l2', title='008 Espresso Test')


if __name__ == '__main__':
    l1_test()
    #l2_test()
    #l1_thrash()
    #dinero_test()
    l1_write_test()
