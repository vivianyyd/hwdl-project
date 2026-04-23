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
        mapping = None,
        latency: float = None,
        flag: int = UNVISITED
    ):
        self.einsum_name = einsum_name
        self.dependencies = dependencies
        self.successors = successors
        self.compute_unit = compute_unit
        self.mapping = mapping
        self.latency = latency
        self.flag = flag

    def __repr__(self):
        return (
            f"({self.einsum_name}, "
            f"{self.compute_unit}, "
            f"latency={self.latency})"
            # f"deps={[dep.einsum_name for dep in self.dependencies]}, "
            # f"succ={[succ.einsum_name for succ in self.successors]}, "
        )


def graph_setup(
    data_dependencies: dict[str, list[str]],
    structural_dependencies: dict[str, list[str]],
    compute_assignment: dict[str, str],
    mapping_grid,
    latency_grid
):
    if mapping_grid is None and latency_grid is None:
        raise ValueError('Need a grid')
    
    nodes = {}
    for name, compute_type in compute_assignment.items():
        mapping = None if mapping_grid is None else mapping_grid[(compute_type, name)]
        latency = mapping.latency() if latency_grid is None else latency_grid[(compute_type, name)]
        nodes[name] = Node(
            name, 
            [], 
            [], 
            compute_type, 
            mapping=mapping,
            latency=latency
        )

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


