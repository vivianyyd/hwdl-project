from scheduling.graph import Node


def assign_time_naive(
    node: Node,
    curr_schedule: dict[Node, float],
    clocks: dict[str, float]
):
    """
    Allocates time for [node] and its dependencies, 
    respecting the current schedule, and clocks.
    """
    if node.flag == Node.DONE:
        return
    if node.flag == Node.VISITED:
        raise ValueError("Cycle in graph")
    
    node.flag = Node.VISITED
    
    for dep in node.dependencies:
        assign_time_naive(dep, curr_schedule, clocks)
    
    # assign a time for this node now that deps all have times
    curr_schedule[node] = max(
        (curr_schedule[dep] + dep.total_latency for dep in node.dependencies),
        default=0
    )
    clocks[node.compute_unit] = curr_schedule[node] + node.total_latency
    
    node.flag = Node.DONE


