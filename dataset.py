import os
import csv
import torch
import numpy as np
from torch.utils.data import Dataset, DataLoader, Subset


class MonteCarloDataset(Dataset):

    def __init__(self, x_dir, y_dir, y_min=None, y_max=None):
        self.x_files = sorted(
            [f for f in os.listdir(x_dir) if f.endswith('.din')])
        self.y_files = sorted(
            [f for f in os.listdir(y_dir) if f.endswith('.csv')])
        self.x_dir = x_dir
        self.y_dir = y_dir

        self.l2_cache_sizes = [
            os.path.splitext(i)[0].split('_')[2] for i in self.x_files
        ]

        if not y_min or not y_max:
            # Compute global min and max values for normalization
            self.y_min = float('inf')
            self.y_max = float('-inf')
            for y_file in self.y_files:
                y_file_path = os.path.join(self.y_dir, y_file)
                with open(y_file_path, 'r') as f:
                    reader = csv.reader(f)
                    cumulative_outputs = [float(row[0]) for row in reader]
                    self.y_min = min(self.y_min, min(cumulative_outputs))
                    self.y_max = max(self.y_max, max(cumulative_outputs))
            print(f"Y min: {self.y_min}. Y max: {self.y_max}")
        else:
            self.y_min = y_min
            self.y_max = y_max

    def __len__(self):
        return len(self.x_files)

    def __getitem__(self, idx):
        x_file = os.path.join(self.x_dir, self.x_files[idx])
        y_file = os.path.join(self.y_dir, self.y_files[idx])

        # Read input data from .din file
        with open(x_file, 'r') as f:
            lines = f.readlines()
            input_data = [[int(x, 16) for x in line.strip().split()]
                          for line in lines]
            input_seq = torch.tensor(input_data, dtype=torch.float32)

        # Read cumulative output data from .csv file
        with open(y_file, 'r') as f:
            reader = csv.reader(f)
            cumulative_outputs = [float(row[0]) for row in reader]
            cumulative_outputs = torch.tensor(cumulative_outputs,
                                              dtype=torch.float32)

        # Normalize cumulative outputs using global min and max values
        cumulative_outputs_norm = (cumulative_outputs -
                                   self.y_min) / (self.y_max - self.y_min)

        # Extract context values from the filename
        context = torch.tensor([
            int(x)
            for x in os.path.splitext(self.x_files[idx])[0].split('_')[1:]
        ],
                               dtype=torch.float32)

        return input_seq, cumulative_outputs_norm, context

    def split_by_cache_size(self, thresh_low=.1, thresh_high=.9):
        sort = np.argsort(self.l2_cache_sizes)
        low = int(thresh_low * len(self))
        high = int(thresh_high * len(self))
        return Subset(self, sort[:low]), Subset(self, sort[low:high]), Subset(
            self, sort[high:])


def get_dataloader(x_dir, y_dir, batch_size, shuffle=True, num_workers=0):
    dataset = MonteCarloDataset(x_dir, y_dir)
    dataloader = DataLoader(dataset,
                            batch_size=batch_size,
                            shuffle=shuffle,
                            num_workers=num_workers)
    return dataloader


if __name__ == '__main__':
    loader = get_dataloader('monte_carlo_tests', 'mc_out', 4, num_workers=4)
    for input_seq, cumulative_outputs, context in loader:
        print(input_seq)
        print(cumulative_outputs)
        print(context)
        break
