import random


class Memory:
    def __init__(self, access_time, static_power, dynamic_power, penalty):
        self.access_time = access_time * 10 ** -9
        self.static_power = static_power
        self.dynamic_power = dynamic_power
        self.penalty = penalty * 10 ** -12
        self.stats = {
            'misses': [],
            'total_energy': 0
        }
        self.next = None

    def calc_if_unused(self, idle_time: float) -> float:
        idle = self.next.calc_if_unused(idle_time) if self.next else 0
        consumed = self.static_power * idle_time + idle
        self.stats['total_energy'] += consumed
        return consumed

    def calc_if_used(self) -> tuple[float, float]:
        consumed = self.dynamic_power * self.access_time + self.penalty
        self.stats['total_energy'] += consumed
        return consumed, self.access_time

    def hit(self) -> float:
        self.stats['misses'].append(0)
        my_consumption = self.calc_if_used()  # First, time to search  myself
        # Then, how much was consumed by subsequent stages during this time
        remaining_idle = self.next.calc_if_unused(self.access_time) if self.next else 0
        # Return total_energy, total_time
        return my_consumption[0] + remaining_idle, self.access_time

    def miss(self, address: int) -> float:
        self.stats['misses'].append(1)
        my_dynamic = self.calc_if_used()  # First, time to search myself
        # How much was consumed by subsequent idle stages during this time
        next_idle = self.next.calc_if_unused(self.access_time) if self.next else 0
        # Then, attempt access on next stage
        future = self.next.access(address)
        # Based on how long it takes, consider that I've been idle for this long
        my_idle = self.calc_if_unused(future[1])
        # Return total_energy, total_time
        return my_dynamic[0] + future[0] + my_idle + next_idle, my_dynamic[1] + future[1]

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
        self.cache_inst = [None] * self.num_blocks
        self.cache_data = [None] * self.num_blocks
        self.next = L2Cache(associativity)

    def access(self, access_type: int, address: int):
        # Determine the cache index based on the address
        index = (address // self.block_size) % self.num_blocks
        cache = self.cache_inst if access_type == 2 else self.cache_data
        # Check if the address is present in the appropriate cache
        if cache[index] == address:
            result = self.hit()
        else:  # Address not found
            cache[index] = address
            result = self.miss(address)
        if access_type == 1:  # Always write to L2 in case we evict here
            additional = self.next.write(address)
            my_idle = self.calc_if_unused(additional[1])
            result = (result[0] + my_idle, result[1] + additional[1])
        return result

    def report(self):
        super().report()
        l1_energy = self.stats['total_energy']
        l2_energy = self.next.stats['total_energy']
        dram_energy = self.next.next.stats['total_energy']
        print(f"Total energy consumed: {l1_energy + l2_energy + dram_energy}")


class L2Cache(Memory):
    def __init__(self, associativity: int):
        super().__init__(5, .8, 2, 5)
        self.cache_size = 256 * 1024  # 256KB
        self.block_size = 64  # 64 bytes per block
        self.associativity = associativity
        self.num_sets = self.cache_size // (self.block_size * self.associativity)
        self.cache = [[[None, False] for _ in range(self.associativity)] for _ in
                      range(self.num_sets)]
        self.next = DRAM()

    def set_index(self, address: int):
        return (address // self.block_size) % self.num_sets

    def find_element(self, address: int):
        set_index = self.set_index(address)
        for i in range(self.associativity):
            if self.cache[set_index][i][0] == address // self.block_size:
                return self.cache[set_index][i]
        return None

    def write(self, address: int):
        result = self.access(address)  # Every write requires an L2 access
        self.find_element(address)[1] = True
        return result

    def access(self, address: int):
        # Check if the address is present in the cache
        if self.find_element(address):
            return self.hit()

        set_index = self.set_index(address)
        # Address not found in the cache
        for idx, val in enumerate(self.cache[set_index]):
            if not val[0]:
                self.cache[set_index][idx][0] = address // self.block_size
                return self.miss(address)
        to_evict = random.randrange(4)
        my_idle = 0
        write_time = 0
        if self.cache[set_index][to_evict][1]:  # If it's modified
            # Assume same consumption for read as write
            result = self.next.access(self.cache[set_index][to_evict][0])
            my_idle = self.calc_if_unused(result[1])
            write_time = result[1]
        self.cache[set_index][to_evict] = [address // self.block_size, False]
        result = self.miss(address)
        return result[0] + my_idle, result[1] + write_time


class DRAM(Memory):
    def __init__(self):
        super().__init__(50, .8, 4, 640)

    def access(self, address: int):
        # pylint: disable=unused-argument
        return self.hit()  # Don't worry about managing memory, always assume a hit

    def report(self):
        print(f"DRAM total energy: {self.stats['total_energy']}")
