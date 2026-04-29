class Node:
    UNVISITED = 0
    VISITED = 1
    DONE = 2

    def __init__(
        self,
        einsum_name: str,
        dependencies: list["Node"], # nodes this node depends on
        successors: list["Node"], # nodes that depend on this node
        compute_assignment,
            # when considering shared memory, this is a tuple (compute, (mem1, percent1), (mem2, percent2), ...)
            # when not considering shared memory, this is simply a string 'compute'
        total_latency: float,
        latencies_per_unit = None,
        actions = None,
        flag: int = UNVISITED
    ):
        self.einsum_name = einsum_name
        self.dependencies = dependencies
        self.successors = successors
        self.compute_assignment = compute_assignment
        self.total_latency = total_latency
        self.latencies_per_unit = latencies_per_unit
        self.actions = actions
        self.flag = flag

    def __repr__(self):
        return (
            f"({self.einsum_name}, "
            f"{self.compute_assignment}, "
            f"latency={self.total_latency})"
            # f"deps={[dep.einsum_name for dep in self.dependencies]}, "
            # f"succ={[succ.einsum_name for succ in self.successors]}, "
        )


def graph_setup(
    data_dependencies: dict[str, list[str]],
    structural_dependencies: dict[str, list[str]],
    compute_assignment,
    latency_per_component_grid = None,
    total_latency_grid = None,
    actions_grid = None,
):
    if latency_per_component_grid is None and total_latency_grid is None:
        raise ValueError('Need a latency grid')

    if latency_per_component_grid is not None and actions_grid is None:
        raise ValueError("Can't do bandwidth-aware scheduling without memory actions")
    
    nodes = {}
    for name, compute_type in compute_assignment.items():
        latencies = None if latency_per_component_grid is None else latency_per_component_grid[(compute_type, name)]
        nodes[name] = Node(
            name, 
            [], 
            [], 
            compute_type,
            total_latency=max(latencies.values()) if total_latency_grid is None else total_latency_grid[(compute_type, name)],
            latencies_per_unit=latencies,
            actions=None if actions_grid is None else actions_grid[(compute_type, name)]
        )

    def add_deps(deps: dict[str, list[str]]):
        for node_name, dep_names in deps.items():
            node = nodes[node_name]
            for dep_name in dep_names:
                dep_node = nodes[dep_name]
                node.dependencies.append(dep_node)
                dep_node.successors.append(node)

    # print("Data deps:", data_dependencies)
    # print("Struct deps:", structural_dependencies)
    add_deps(data_dependencies)
    add_deps(structural_dependencies)

    return nodes


