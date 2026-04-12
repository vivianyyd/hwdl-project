import itertools

class Node:
    UNVISITED = 0
    VISITED = 1
    DONE = 2

    def __init__(
        self,
        einsum_name: str,
        dependencies: list["Node"], # nodes this node depends on
        successors: list["Node"], # nodes that depend on this node
        compute_unit: str,
        latency: float,
        flag: int = UNVISITED
    ):
        self.einsum_name = einsum_name
        self.dependencies = dependencies
        self.successors = successors
        self.compute_unit = compute_unit
        self.latency = latency
        self.flag = flag

    def __repr__(self):
        return (
            f"Node({self.einsum_name}, "
            f"compute={self.compute_unit}, "
            f"deps={[dep.einsum_name for dep in self.dependencies]}, succ={[succ.einsum_name for succ in self.successors]}, "
            f"latency={self.latency})"
        )


def assign_times(untimed_schedule: list[Node]) -> tuple[dict[Node, float], float]:
    """
    Returns the optimal timed schedule and the latency.
    """
    curr_schedule = {}
    clocks = {}
    for node in untimed_schedule:
        if not node.successors: # node is a leaf
            assign_time(node, curr_schedule, clocks)
    return curr_schedule, max(clocks.values())


def assign_time(
    node: Node,
    curr_schedule: dict[Node, float],
    clocks: dict[str, float]
):
    if node.flag == Node.DONE:
        return
    if node.flag == Node.VISITED:
        raise ValueError("Cycle in graph")
    
    node.flag = Node.VISITED
    
    for dep in node.dependencies:
        assign_time(dep, curr_schedule, clocks)
    
    # assign a time for this node now that deps all have times
    curr_schedule[node] = max(
        (curr_schedule[dep] + dep.latency for dep in node.dependencies), 
        default=0
    )
    clocks[node.compute_unit] = curr_schedule[node] + node.latency
    
    node.flag = Node.DONE


def placements(einsums: list[str], units: list[str]):
    """
    Generates all possible assignments of einsums to compute units. 
    Things that look like: 
    {'e1': 'fast', 'e2': 'slow', 'e3': 'fast'}
    """
    return [
        dict(zip(einsums, values))
        for values in itertools.product(units, repeat=len(einsums))
    ]


def graph_setup(
    data_dependencies: dict[str, list[str]],
    structural_dependencies: dict[str, list[str]],
    compute_assignment: dict[str, str],
    grid: dict[str, dict[str, float]]
):
    nodes = {}
    for name, compute_type in compute_assignment.items():
        nodes[name] = Node(name, [], [], compute_type, grid[name][compute_type])

    def add_deps(deps: dict[str, list[str]]):
        for node_name, dep_names in deps.items():
            node = nodes[node_name]
            for dep_name in dep_names:
                dep_node = nodes[dep_name]
                node.dependencies.append(dep_node)
                dep_node.successors.append(node)

    add_deps(data_dependencies)
    add_deps(structural_dependencies)

    return nodes
