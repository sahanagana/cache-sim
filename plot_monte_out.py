import os
#import random
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm

if __name__ == '__main__':
    data = []
    for i in tqdm(os.listdir('mc_out')):
        with open(f"mc_out/{i}", 'r') as f:
            final_energy = float(f.readlines()[-1])
        l1, l2 = i.split('.')[0].split('_')[1:]
        data.append({'l1': int(l1), 'l2': int(l2), 'energy': final_energy})
    data = pd.DataFrame(data)
    #    data = pd.read_csv(f'mc_out/{i}', names=['energy'])
    plt.scatter(data['l2'], data['energy'], marker='.', alpha=.2)
    plt.xlabel('L2 Cache Size')
    plt.ylabel('Total Energy Consumption')
    plt.title('Energy Consumption and Cache Size')
    plt.show()
