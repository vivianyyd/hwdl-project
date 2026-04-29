from scheduling.graph import *
from scheduling.util import *
from scheduling.talloc_bw import *
from scheduling.talloc_naive import *
from scheduling.talloc_share_mem import *


def assign_times(untimed_schedule: list[Node], memory_name, shared_memory_info) -> tuple[dict[Node, float], float]:
    """
    Returns the optimal timed schedule and the latency.

    shared_memory_info is only really used as a flag here to tell that we should call the tallocator that considers shared memory capacity.
    """
    curr_schedule = {}
    clocks = {}
    for node in untimed_schedule:
        if not node.successors: # node is a leaf
            if shared_memory_info != None:
                assign_time_shared_mem(node, memory_name, curr_schedule, clocks, [])
            if memory_name == None:
                assign_time_naive(node, curr_schedule, clocks)
            else:
                assign_time_bwu(node, memory_name, curr_schedule, clocks, [])
    return curr_schedule, max(clocks.values())


def best_schedule(
    einsums,
    compute_units,  # list of compute unit names. e.g. ['c1', 'c2', 'c3']
    shared_memory_info,
        # only includes shared memory that has a capacity (i.e. DRAM not included)
        # {memory unit name : list of valid partitions to compute units}
        # for example,
        # {'m1' : [(50, 25, 25), (25, 50, 25), ...], 'm2' : [(0, 0, 100), (50, 25, 25), ...]}
        # for an architecture with 2 shared memory levels and 3 compute units.
        # the first (resp. second, third) element in each 3-tuple is the memory allocated to c1 (resp. c2, c3).
    data_dependencies,
    latency_per_component_grid,
    total_latency_grid,
    actions_grid,
    memory_name
):
    best_schedule = None
    min_latency = float('inf')

    architecture_pairings = generate_architecture_pairings(compute_units, shared_memory_info)
    
    for compute_assignment in placements(einsums, architecture_pairings):
        for structural_dependencies in untimed_schedules(compute_assignment, data_dependencies, compute_units):
            # print("A new untimed schedule")
            
            nodes = graph_setup(
                data_dependencies,
                structural_dependencies,
                compute_assignment,
                latency_per_component_grid,
                total_latency_grid,
                actions_grid,
            )
            # print(nodes)
            # print()
            # print()
            try:
                schedule, latency = assign_times(nodes.values(), memory_name, shared_memory_info)
                if latency < min_latency:
                    best_schedule = schedule
                    min_latency = latency
            # we can get a cycle in the graph from a bad topological sort...
            #  think about this a lil later
            except ValueError as e:
                print(f"Error: {e}")
            
            

    return best_schedule, min_latency

