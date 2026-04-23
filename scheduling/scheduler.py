from scheduling.graph import *
from scheduling.util import *
from scheduling.talloc_bw import *
from scheduling.talloc_naive import *


def assign_times(untimed_schedule: list[Node], memory_name) -> tuple[dict[Node, float], float]:
    """
    Returns the optimal timed schedule and the latency.
    """
    curr_schedule = {}
    clocks = {}
    for node in untimed_schedule:
        if not node.successors: # node is a leaf
            if memory_name == None:
                assign_time_naive(node, curr_schedule, clocks)
            else:
                assign_time_bwu(node, memory_name, curr_schedule, clocks, [])
    return curr_schedule, max(clocks.values())


def best_schedule(
    einsums,
    compute_units,
    data_dependencies,
    latency_per_component_grid,
    total_latency_grid,
    actions_grid,
    memory_name
):
    best_schedule = None
    min_latency = float('inf')
    for compute_assignment in placements(einsums, compute_units):
        for structural_dependencies in untimed_schedules(compute_assignment, data_dependencies, compute_units):
            nodes = graph_setup(
                data_dependencies,
                structural_dependencies,
                compute_assignment,
                latency_per_component_grid,
                total_latency_grid,
                actions_grid,
            )
            schedule, latency = assign_times(nodes.values(), memory_name)
            if latency < min_latency:
                best_schedule = schedule
                min_latency = latency

    return best_schedule, min_latency

