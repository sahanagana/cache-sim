import random
import math


class Usage:
    """
    Abstractly represents consumption of system resources (energy and time)
    """
    def __init__(self, energy=0, time=0):
        self.energy, self.time = energy, time

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
    # pylint: disable=too-many-instance-attributes
    """
    Abstract Memory storage unit. Stores hardware specs and is responsible for power calculations.
    """
    def __init__(self, access_time, static_power, dynamic_power, penalty):
        self.access_time = access_time * 1e-9
        self.static_power = static_power
        self.dynamic_power = dynamic_power
        self.penalty = penalty * 1e-12
        self.stats = {
            'my_accesses': 0,
            'my_misses': 0,
            'my_energy': [],
            'my_time': []
        }
        self.next = None
        self.next: Memory
        self.dynamic_usage = Usage()
        self.static_usage = Usage()

    def tag_to_addr(self, tag: int, index: int):
        """
        Abstract method, returns address for given tag
        """

    def access(self, access_type: int, address: int, from_previous=False) -> Usage:
        # pylint: disable=unused-argument
        """
        Abstract method, returns my_usage, future_usage after access was attempted. This super
        method adds the penalty to the current dynamic_usage.
        from_previous: whether the data is being received from previous level in hierarchy.
        """
        self.dynamic_usage.energy += self.penalty

    def update_stats(self, do_next=True):
        """
        Update the stats based on the total usage after the access is complete. Must be called at
        the end of access().
        """
        self.stats['my_energy'].append(self.dynamic_usage.energy + self.static_usage.energy)
        if not do_next:
            self.stats['my_time'].append(self.dynamic_usage.time + self.static_usage.time)
            future_times = []
        else:
            future_times = self.next.update_stats() if self.next else []
            self.stats['my_time'].append(self.dynamic_usage.time + self.static_usage.time -
                                         sum(future_times))
        self.dynamic_usage = Usage()
        self.static_usage = Usage()
        return [self.stats['my_time'][-1], *future_times]

    def idle(self, idle_time: float, next_idle=True) -> float:
        """
        If we're idle for idle_time, return/log how much energy was consumed
        """
        # Everything below us was also idle, so add that result
        if self.next and next_idle:
            self.next.idle(idle_time, next_idle=next_idle)
        consumed = self.static_power * idle_time
        self.static_usage += Usage(consumed, idle_time)

    def use(self):
        """
        Dynamic use of this device. Log to current usage.
        """
        consumed = self.dynamic_power * self.access_time
        self.dynamic_usage += Usage(consumed, self.access_time)

    def hit(self):
        """
        Handle a cache hit.
        """
        self.stats['my_accesses'] += 1
        if self.next:
            self.next.idle(self.dynamic_usage.time)  # No future static consumption if we have a hit

    def miss(self, access_type: int, address: int, from_previous=False):
        """
        Handle a cache miss.
        """
        self.hit()  # From an energy perspective, we must first behave as if we'd had a hit
        if not from_previous:
            # Then, attempt access on next stage
            self.next.access(access_type, address)
            # Based on how long it takes, consider that I've been idle for this long
            self.idle(self.next.dynamic_usage.time + self.next.static_usage.time, next_idle=False)
        if access_type == 1:  # If we're writing
            self.use()  # Another use to write the data

    def handle_eviction(self, cache, index):
        """
        Decide whether we need to evict, and evict if so. Account for energy as needed.
        """
        if cache[index][0] is None or not cache[index][1]:
            return
        # If we're here, we're evicting a modified cache line
        self.next.access(1, self.tag_to_addr(cache[index][0], index), from_previous=True)
        # Our idle consumption
        self.idle(self.next.dynamic_usage.time + self.next.static_usage.time, next_idle=False)

    def report(self, stat: str, do_next=True):
        """
        Return appropriate stat for this and all lower levels.
        """
        if stat == 'Misses':
            my = self.stats['my_misses']
        elif stat == 'Accesses':
            my = self.stats['my_accesses']
        elif stat == 'Energy':
            my = self.stats['my_energy']
        elif stat == 'Time':
            my = self.stats['my_time']
        return [my, *(self.next.report(stat) if self.next and do_next else [])]


class MemorySystem:
    """
    Main memory system imported and used outside of this file. Top level of hierarchy.
    """
    def __init__(self, associativity=4, l1_size=32*1024, l2_size=256*1024, random_seed=None):
        l2 = L2Cache(associativity, l2_size, random_seed=random_seed)
        # caches: icache (index 0), dcache (index 1)
        self.caches = (L1Cache(l2, l1_size), L1Cache(l2, l1_size))

    def access(self, access_type: int, address: int):
        """
        Access an address. Calls icache or dcache depending on access_type.
        """
        self.caches[access_type != 2].access(access_type, address)
        idle_time = self.caches[access_type != 2].update_stats()
        self.caches[access_type == 2].idle(sum(idle_time))
        self.caches[access_type == 2].update_stats(do_next=False)

    def report(self, stat: str):
        """
        Different report including icache and dcache.
        """
        l1 = self.caches[0].report(stat)
        # order: icache, dcache, l2, dram
        l1.insert(1, self.caches[1].report(stat, do_next=False)[0])
        return l1


class L1Cache(Memory):
    def __init__(self, next_mem: Memory, l1_size: int):
        super().__init__(.05, .5, 1, 0)  # Set the hardware parameters
        self.cache_size = l1_size
        self.block_size = 64  # 64 bytes per block
        self.num_blocks = self.cache_size // self.block_size
        # THIS CREATES A LIST OF POINTERS, NOT MODIFY-SAFE
        self.cache = [[None, False]] * self.num_blocks
        self.next = next_mem

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
        super().access(access_type, address, from_previous)
        # Determine the cache index based on the address
        index, tag = self.parse_addr(address)
        self.use()  # Read operation
        # Check if the address is present in the appropriate cache
        if self.cache[index][0] == tag:
            self.hit()  # Defined in superclass
            # Set the modified bit (but don't write through, we're doing write back)
            self.cache[index] = [tag, True if access_type == 1 else self.cache[index][1]]
        else:  # Address not found
            self.handle_eviction(self.cache, index)  # Returns Usage after eviction
            self.cache[index] = [tag, access_type == 1]  # MUST set like this
            self.miss(access_type, address, from_previous=from_previous)


class L2Cache(Memory):
    """
    Second level of memory system, set-associative mapping.
    """
    def __init__(self, associativity: int, l2_size: int, random_seed=None):
        super().__init__(4.5, .8, 2, 5)  # Set hardware parameters
        self.cache_size = l2_size
        self.block_size = 64  # 64 bytes per block
        self.associativity = associativity
        self.num_sets = self.cache_size // (self.block_size * self.associativity)
        self.cache = SetAssociativeCache([[[None, False] for _ in range(self.associativity)]
                                          for _ in range(self.num_sets)])
        self.cache: SetAssociativeCache  # Type hint suppresses linting "errors"
        self.rng = random.Random(random_seed)
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
        super().access(access_type, address, from_previous)
        # Check if the address is present in the cache
        if elem := self.find_element(address):
            if access_type == 1:
                self.cache[elem[0]][elem[1]][1] = True
            self.hit()
            return

        set_index, tag = self.parse_addr(address)
        # Address not found in the cache
        for idx, val in enumerate(self.cache[set_index]):
            self.use()
            if val[0] is None:  # No eviction needed
                self.cache[set_index][idx] = [tag, access_type == 1]
                self.miss(access_type, address, from_previous=from_previous)
                return
        # Now we're evicting
        to_evict = self.rng.randrange(self.associativity)  # Random eviction policy
        self.use()  # Access this random index
        self.handle_eviction(self.cache, (set_index, to_evict))
        self.cache[set_index][to_evict] = [tag, access_type == 1]
        self.miss(access_type, address, from_previous=from_previous)


class DRAM(Memory):
    """
    Lowest level in the hierarchy. No misses here (assumption).
    """
    def __init__(self):
        super().__init__(45, .8, 4, 640)  # Hardware params

    def access(self, access_type: int, address: int, from_previous=False):
        # pylint: disable=unused-argument
        """
        Very simple access method: always a hit.
        """
        self.use()
