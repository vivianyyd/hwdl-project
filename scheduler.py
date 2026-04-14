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
            f"({self.einsum_name}, "
            f"compute={self.compute_unit}, "
            # f"deps={[dep.einsum_name for dep in self.dependencies]}, "
            # f"succ={[succ.einsum_name for succ in self.successors]}, "
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


def restricted_dependencies(data_dependencies, subset):
    # For each hardware component, generate a dependency graph consisting of only Einsums assigned to that component.    
    # This is not a strict subgraph of the original dependency graph. We need to instead propagate dependencies from the original graph. For example, if C depends on B depends on A, but only A and C are scheduled for some hardware component H, the dependency graph for H must include an edge between A and C.
    result = {node: [] for node in subset}

    for start in subset:
        visited = set()
        direct = set()

        stack = list(data_dependencies.get(start, []))
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)

            if node in subset:
                # Found a subset node reachable from start:
                # record edge start -> node, but don't go past it
                direct.add(node)
            else:
                # Not in subset: keep going through its dependencies
                stack.extend(data_dependencies.get(node, []))

        result[start] = list(direct)

    return result


def all_topological_sorts(dependency_graph):
    nodes = set(dependency_graph.keys())

    # Initialize indegree and reverse adjacency (node -> list of nodes that depend on it)
    indegree = {}
    children = {}
    for n in nodes:
        indegree[n] = 0
        children[n] = []

    for node, deps in dependency_graph.items():
        for d in deps:
            indegree[node] += 1      # node has one more prerequisite
            children[d].append(node) # d -> node

    result = []
    current_order = []

    def dfs():
        # Find all nodes that are available to place next: indegree 0 and not used yet
        available = [n for n in nodes if indegree[n] == 0 and n not in current_order]

        if not available:
            # If we've placed all nodes, we got one full topological order
            if len(current_order) == len(nodes):
                result.append(list(current_order))
            return

        # Try each available node as the next in the order
        for n in available:
            # Choose n
            current_order.append(n)
            # Temporarily "remove" n: reduce indegree of its children
            changed = []
            for ch in children[n]:
                indegree[ch] -= 1
                changed.append(ch)

            # Recurse
            dfs()

            # Backtrack
            for ch in changed:
                indegree[ch] += 1
            current_order.pop()

    dfs()
    return result


def structural_deps(toposort: list[str]):
    result = {}
    if not toposort:
        return result
    result[toposort[0]] = []
    for i in range(1, len(toposort)):
        curr = toposort[i]
        prev = toposort[i - 1]
        result[curr] = [prev]
    return result


def labelled_cartesian_product(d):
    """
    d: dict[str, list[dict]]
    Return a list of dicts, each formed by taking exactly one dict
    from each list in d, and merging them.
    Assumes all keys in all dicts are disjoint; no conflict handling.
    """
    items = list(d.items())
    if not items:
        return []

    result = []

    def dfs(i, current):
        if i == len(items):
            # Reached a full combination
            result.append(current.copy())
            return

        key, dict_list = items[i]
        # For each dict at this label, extend current
        for choice in dict_list:
            # Merge choice into current; assume disjoint keys
            # so we can just update
            current.update(choice)
            dfs(i + 1, current)
            # Backtrack: remove choice's keys from current
            for k in choice:
                current.pop(k, None)

    dfs(0, {})
    return result


def untimed_schedules(
    compute_assignment: dict[str, str],
    data_dependencies: dict[str, list[str]],
    compute_units: list[str]
):
    """
    Returns a list of all possible untimed schedules, represented as structural
    dependencies between einsums. Structural dependencies occur exactly between
    two einsums that happen one after another on the same compute unit.
    """
    # For each untimed schedule, return it in the form of
    # mapping each einsum to a list containing the one that happens right before it on the 
    # same compute unit, or the empty list if it is the first to execute on that compute 
    # unit. Then perform a topological sort of this restricted dependency graph to generate
    # an order in which Einsums are to be computed on each component.
    compute_unit_schedules = {}
    for compute in compute_units:
        # For debugging
        # print(
        #     "\tEinsums restricted to", compute, 
        #     [e for e, c in compute_assignment.items() if c == compute]
        # )
        restricted_deps = restricted_dependencies(
            data_dependencies, 
            [e for e, c in compute_assignment.items() if c == compute]
        )
        # print("\t\tRestricted deps:", restricted_deps) # debugging
        toposorts = all_topological_sorts(restricted_deps)

        compute_unit_schedules[compute] = [
            structural_deps(t)
            for t in toposorts
        ]
    return labelled_cartesian_product(compute_unit_schedules)

