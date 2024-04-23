import random
import math


class Usage:
    """
    Abstractly represents consumption of system resources (energy and time)
    """
    def __init__(self, energy=0, time=0):
        self.energy, self.time = energy, time
        self.idle_time = 0

    def __add__(self, other):
        """
        Overrides the + operation so that two Usage objects can easily be added together
        """
        if isinstance(other, Usage):
            self.energy += other.energy
            self.time += other.time
            return self  # Because we generally do += or set a pointer to this result
        if isinstance(other, int):
            pass  # do something
        raise ValueError()  # This should never happen

    def __radd__(self, other):
        """
        Addition should be commutative, so if we try adding in the wrong order, call normal add
        """
        return self.__add__(other)


class SetAssociativeCache(list):
    """
    A special type of list which can accept tuple indices.
    """
    def __getitem__(self, index):
        """
        Overrides list.__getitem__ to change the behavior of list indexing.
        """
        if isinstance(index, tuple):
            return self[index[0]][index[1]]
        return super().__getitem__(index)


class Memory:
    """
    Abstract Memory storage unit. Stores hardware specs and is responsible for power calculations.
    """
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
        self.next: Memory
        self.usage = Usage(energy=self.penalty)

    def tag_to_addr(self, tag: int, index: int):
        """
        Abstract method, returns address for given tag
        """

    def access(self, access_type: int, address: int, from_previous=False) -> Usage:
        """
        Abstract method, returns Usage after access was attempted.
        from_previous: whether the data is being received from previous level in hierarchy.
        """

    def calc_if_unused(self, idle_time: float, next_idle=True) -> float:
        """
        If we're idle for idle_time, return how much energy was consumed
        """
        # Everything below us was also idle, so add that result
        idle = self.next.calc_if_unused(idle_time, next_idle) if self.next and next_idle else 0
        consumed = self.static_power * idle_time + idle
        self.stats['total_energy'] += consumed
        return consumed

    def use(self):
        """
        Dynamic use of this device. Log to current usage.
        """
        consumed = self.dynamic_power * self.access_time
        self.stats['total_energy'] += consumed
        self.usage += Usage(consumed, self.access_time)

    def total_usage(self) -> Usage:
        """
        Returns the total usage so far (including subsequent idle time), and clears the usage.
        """
        # idle_time tracks how long out of time that we weren't operating, therefore subsequent
        # stages were operating, therefore those stages were not idle, so the energy consumption
        # is already factored in elsewhere.
        self.usage.energy += self.next.calc_if_unused(self.usage.time - self.usage.idle_time) if \
            self.next else 0
        result = self.usage
        self.usage = Usage(energy=self.penalty)
        return result

    def hit(self) -> Usage:
        """
        Handle a cache hit.
        """
        self.stats['misses'].append(0)
        my_usage = self.total_usage()
        return my_usage

    def miss(self, access_type: int, address: int, from_previous=False) -> Usage:
        """
        Handle a cache miss.
        """
        self.stats['misses'].append(1)  # All this is for the read
        my_consumption = self.total_usage()
        if not from_previous:
            # Then, attempt access on next stage
            future = self.next.access(access_type, address)
            self.usage.idle_time += future.time
            # Based on how long it takes, consider that I've been idle for this long
            my_consumption.energy += self.calc_if_unused(future.time, next_idle=False)
        else:  # Transferred from previous
            future = Usage()  # Transfer penalty was factored in at beginning
        if access_type == 1:  # If we're writing
            self.use()  # Another use to write the data
            my_consumption += self.total_usage()
        return my_consumption + future  # Return total Usage

    def handle_eviction(self, cache, index):
        """
        Decide whether we need to evict, and evict if so. Account for energy as needed.
        """
        if cache[index][0] is None or not cache[index][1]:
            return Usage()  # We aren't evicting/evicting an unmodified cache line
        # If we're here, we're evicting a modified cache line
        result = self.next.access(1, self.tag_to_addr(cache[index][0], index), from_previous=True)
        self.usage.idle_time += result.time
        # Add our idle consumption
        result.energy += self.calc_if_unused(result.time, next_idle=False)
        return result

    def report(self):
        """
        Print # misses, # hits, energy consumed for each level
        """
        print(f"{self.__class__.__name__} Misses: {sum(self.stats['misses'])}")
        print(f"{self.__class__.__name__} Hits: {sum(1 - i for i in self.stats['misses'])}")
        print(f"{self.__class__.__name__} Energy: {self.stats['total_energy']}")
        if self.next:
            self.next.report()


class L1Cache(Memory):
    """
    Main memory system imported and used outside of this file. Top level of hierarchy.
    """
    def __init__(self, associativity=4):
        super().__init__(.05, .5, 1, 0)  # Set the hardware parameters
        self.cache_size = 32 * 1024  # 32KB
        self.block_size = 64  # 64 bytes per block
        self.num_blocks = self.cache_size // self.block_size
        # THIS CREATES A LIST OF POINTERS, NOT MODIFY-SAFE
        self.cache_inst = [[None, False]] * self.num_blocks
        self.cache_data = [[None, False]] * self.num_blocks
        self.next = L2Cache(associativity)  # Pass through associativity argument

    def parse_addr(self, address: int) -> tuple[int, int]:
        """
        Given an address, return (index, tag) showing where in cache it is.
        """
        return (address >> 6) & (self.num_blocks - 1), \
            address >> (6 + int(math.log2(self.num_blocks)))

    def tag_to_addr(self, tag: int, index: int):
        """
        Inverse parse_addr: given a tag & index, return an address which would hit that cache line.
        """
        return (tag << (6 + int(math.log2(self.num_blocks)))) | (index << 6)

    def access(self, access_type: int, address: int, from_previous=False):
        """
        Implements the access method for L1.
        """
        # Determine the cache index based on the address
        index, tag = self.parse_addr(address)
        cache = self.cache_inst if access_type == 2 else self.cache_data
        self.use()  # Read operation
        # Check if the address is present in the appropriate cache
        if cache[index][0] == tag:
            result = self.hit()  # Defined in superclass
            # Set the modified bit (but don't write through, we're doing write back)
            cache[index] = [tag, True if access_type == 1 else cache[index][1]]
        else:  # Address not found
            result = self.handle_eviction(cache, index)  # Returns Usage after eviction (if needed)
            cache[index] = [tag, access_type == 1]  # MUST set like this because of pointer list
            result += self.miss(access_type, address, from_previous=from_previous)
        return result

    def report(self):
        """
        Additionally print the total energy for the whole system.
        """
        super().report()
        l1_energy = self.stats['total_energy']
        l2_energy = self.next.stats['total_energy']
        dram_energy = self.next.next.stats['total_energy']
        print(f"Total energy consumed: {l1_energy + l2_energy + dram_energy}")


class L2Cache(Memory):
    """
    Second level of memory system, set-associative mapping.
    """
    def __init__(self, associativity: int):
        super().__init__(4.5, .8, 2, 5)  # Set hardware parameters
        self.cache_size = 256 * 1024  # 256KB
        self.block_size = 64  # 64 bytes per block
        self.associativity = associativity
        self.num_sets = self.cache_size // (self.block_size * self.associativity)
        self.cache = SetAssociativeCache([[[None, False] for _ in range(self.associativity)]
                                          for _ in range(self.num_sets)])
        self.cache: SetAssociativeCache  # Type hint suppresses linting "errors"
        self.next = DRAM()

    def parse_addr(self, address: int):
        """
        Returns index, tag (see superclass)
        """
        return (address >> 6) & (self.num_sets - 1), \
            (address >> (6 + int(math.log2(self.num_sets))))

    def tag_to_addr(self, tag: int, index: tuple[int, int]):
        """
        From tag, index (as tuple), returns address which hits the same cache line (see superclass)
        """
        return (tag << (6 + int(math.log2(self.num_sets)))) | (index[0] << 6)

    def find_element(self, address: int):
        """
        Given an address, attempt to find the element in the cache.
        """
        set_index, tag = self.parse_addr(address)
        for i in range(self.associativity):
            self.use()
            if self.cache[set_index][i][0] == tag:
                return set_index, i
        return None

    def access(self, access_type: int, address: int, from_previous=False):
        """
        Handle accessing this unit (see superclass & L1)
        """
        # Check if the address is present in the cache
        if elem := self.find_element(address):
            if access_type == 1:
                self.cache[elem[0]][elem[1]][1] = True
            return self.hit()

        set_index, tag = self.parse_addr(address)
        # Address not found in the cache
        for idx, val in enumerate(self.cache[set_index]):
            self.use()
            if val[0] is None:  # No eviction needed
                self.cache[set_index][idx] = [tag, access_type == 1]
                return self.miss(access_type, address, from_previous=from_previous)
        # Now we're evicting
        to_evict = random.randrange(self.associativity)  # Random eviction policy
        self.use()  # Access this random index
        result = self.handle_eviction(self.cache, (set_index, to_evict))
        self.cache[set_index][to_evict] = [tag, access_type == 1]
        result += self.miss(access_type, address, from_previous=from_previous)
        return result


class DRAM(Memory):
    """
    Lowest level in the hierarchy. No misses here (assumption).
    """
    def __init__(self):
        super().__init__(45, .8, 4, 640)  # Hardware params

    def access(self, access_type: int, address: int, from_previous=False):
        """
        Very simple access method: always a hit.
        """
        # pylint: disable=unused-argument
        return self.hit()  # Don't worry about managing memory, always assume a hit

    def report(self):
        """
        Don't report hit/miss statistics since they're meaningless.
        """
        print(f"DRAM total energy: {self.stats['total_energy']}")
