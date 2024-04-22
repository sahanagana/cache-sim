import random
import math


class Usage:
    def __init__(self, energy=0, time=0):
        self.energy, self.time = energy, time

    def __add__(self, other):
        if isinstance(other, Usage):
            self.energy += other.energy
            self.time += other.time
            return self
        return self + other

    def __radd__(self, other):
        return self.__add__(other)


class SetAssociativeCache(list):
    def __getitem__(self, index):
        if isinstance(index, tuple):
            return self[index[0]][index[1]]
        return super().__getitem__(index)


class Memory:
    def __init__(self, access_time, static_power, dynamic_power, penalty):
        self.access_time = access_time * 1e-9
        self.static_power = static_power
        self.dynamic_power = dynamic_power
        self.penalty = penalty * 1e-12
        self.stats = {
            'misses': [],
            'total_energy': 0
        }
        self.next = None
        self.usage = Usage()

    def tag_to_addr(self, tag: int, index: int):
        """
        Abstract method, returns address for given tag
        """

    def calc_if_unused(self, idle_time: float) -> float:
        idle = self.next.calc_if_unused(idle_time) if self.next else 0
        consumed = self.static_power * idle_time + idle
        self.stats['total_energy'] += consumed
        return consumed

    def use(self):
        consumed = self.dynamic_power * self.access_time + self.penalty
        self.stats['total_energy'] += consumed
        self.usage += Usage(consumed, self.access_time)

    def total_usage(self) -> Usage:
        """
        Returns the total usage so far (including subsequent idle time), and clears the usage.
        """
        self.usage.energy += self.next.calc_if_unused(self.usage.time) if self.next else 0
        result = self.usage
        self.usage = Usage()
        return result

    def hit(self) -> Usage:
        self.stats['misses'].append(0)
        return self.total_usage()

    def miss(self, access_type: int, address: int) -> Usage:
        self.stats['misses'].append(1)  # All this is for the read
        my_consumption = self.total_usage()
        # Then, attempt access on next stage
        future = self.next.access(access_type, address)
        # Based on how long it takes, consider that I've been idle for this long
        my_consumption.energy += self.calc_if_unused(future.time)
        if access_type == 1:  # If we're writing
            self.use()
            my_consumption += self.total_usage()
        return my_consumption + future

    def handle_eviction(self, cache, index):
        if cache[index][0] is None or not cache[index][1]:
            return Usage()
        result = self.next.access(1, self.tag_to_addr(cache[index][0], index))  # Write to L2
        # Add our idle + penalty because we had to transfer the data to L2
        result.energy += self.calc_if_unused(result.time) + self.penalty
        return result

    def report(self):
        print(f"{self.__class__.__name__} Misses: {sum(self.stats['misses'])}")
        print(f"{self.__class__.__name__} Hits: {sum(1 - i for i in self.stats['misses'])}")
        print(f"{self.__class__.__name__} Energy: {self.stats['total_energy']}")
        if self.next:
            self.next.report()


class L1Cache(Memory):
    # pylint: disable=arguments-differ
    def __init__(self, associativity=4):
        super().__init__(.05, .5, 1, 0)
        self.cache_size = 32 * 1024  # 32KB
        self.block_size = 64  # 64 bytes per block
        self.num_blocks = self.cache_size // self.block_size
        # THIS CREATES A LIST OF POINTERS, NOT MODIFY-SAFE
        self.cache_inst = [[None, False]] * self.num_blocks
        self.cache_data = [[None, False]] * self.num_blocks
        self.next = L2Cache(associativity)

    def tag_to_addr(self, tag: int, index: int):
        return (tag << (6 + int(math.log2(self.num_blocks)))) | (index << 6)

    def parse_addr(self, address: int):
        return (address >> 6) & (self.num_blocks - 1), \
            address >> (6 + int(math.log2(self.num_blocks)))

    def access(self, access_type: int, address: int):
        # Determine the cache index based on the address
        index, tag = self.parse_addr(address)
        cache = self.cache_inst if access_type == 2 else self.cache_data
        self.use()  # Read operation
        # Check if the address is present in the appropriate cache
        if cache[index][0] == tag:
            result = self.hit()
        else:  # Address not found
            result = self.handle_eviction(cache, index)
            cache[index] = [tag, access_type == 1]  # MUST set like this because of pointer list
            result += self.miss(access_type, address)
        return result

    def report(self):
        super().report()
        l1_energy = self.stats['total_energy']
        l2_energy = self.next.stats['total_energy']
        dram_energy = self.next.next.stats['total_energy']
        print(f"Total energy consumed: {l1_energy + l2_energy + dram_energy}")


class L2Cache(Memory):
    def __init__(self, associativity: int):
        super().__init__(4.5, .8, 2, 5)
        self.cache_size = 256 * 1024  # 256KB
        self.block_size = 64  # 64 bytes per block
        self.associativity = associativity
        self.num_sets = self.cache_size // (self.block_size * self.associativity)
        self.cache = SetAssociativeCache([[[None, False] for _ in range(self.associativity)]
                                          for _ in range(self.num_sets)])
        self.cache: SetAssociativeCache  # Type hint suppresses linting "errors"
        self.next = DRAM()

    def parse_addr(self, address: int):
        return (address >> 6) & (self.num_sets - 1), \
            (address >> (6 + int(math.log2(self.num_sets))))

    def tag_to_addr(self, tag: int, index: tuple[int, int]):
        return (tag << (6 + int(math.log2(self.num_sets)))) | (index[0] << 6)

    def find_element(self, address: int):
        set_index, tag = self.parse_addr(address)
        for i in range(self.associativity):
            self.use()
            if self.cache[set_index][i][0] == tag:
                return self.cache[set_index][i]
        return None

    def access(self, access_type: int, address: int):
        # Check if the address is present in the cache
        if self.find_element(address):
            return self.hit()

        set_index, tag = self.parse_addr(address)
        # Address not found in the cache
        for idx, val in enumerate(self.cache[set_index]):
            self.use()
            if not val[0]:
                self.cache[(set_index, idx)][0] = tag
                return self.miss(access_type, address)
        to_evict = random.randrange(self.associativity)
        self.use()  # Access this random index
        result = self.handle_eviction(self.cache, (set_index, to_evict))
        self.cache[set_index][to_evict] = [tag, access_type == 1]
        result += self.miss(access_type, address)
        return result


class DRAM(Memory):
    def __init__(self):
        super().__init__(45, .8, 4, 640)

    def access(self, access_type: int, address: int):
        # pylint: disable=unused-argument
        return self.hit()  # Don't worry about managing memory, always assume a hit

    def report(self):
        print(f"DRAM total energy: {self.stats['total_energy']}")
