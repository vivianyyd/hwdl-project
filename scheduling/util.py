import itertools
# This file contains graph traversals and combinatorial-blowup helper functions


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


def restricted_dependencies(data_dependencies: dict[str, list[str]], subset: list[str]):
    # For each hardware component, generate a dependency graph consisting of only Einsums assigned to that component.
    # [subset] contains the Einsums for the current component.
    # [data_dependencies] contains all dependencies in the entire graph.
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
        restricted_deps = restricted_dependencies(
            data_dependencies, 
            [e for e, c in compute_assignment.items() if c == compute]
        )
        toposorts = all_topological_sorts(restricted_deps)

        
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

        
        compute_unit_schedules[compute] = [
            structural_deps(t)
            for t in toposorts
        ]
    return labelled_cartesian_product(compute_unit_schedules)



def generate_architecture_pairings(
    compute_units,  # list of compute unit names. e.g. ['c1', 'c2', 'c3']
    shared_memory_info,
        # only includes shared memory that has a capacity (i.e. DRAM not included)
        # {memory unit name : list of valid partitions to compute units}
        # for example,
        # {'m1' : [(50, 25, 25), (25, 50, 25), ...], 'm2' : [(0, 0, 100), (50, 25, 25), ...]}
        # for an architecture with 2 shared memory levels and 3 compute units.
        # the first (resp. second, third) element in each 3-tuple is the memory allocated to c1 (resp. c2, c3).
):
    """
    from shared_memory_info and compute_units, generate a list of tuples
    following the examples above, we should generate a list of the form
    [('c1', ('m1', 50), ('m2', 0)), ('c1', ('m1', 50), ('m2', 50)),
     ('c1', ('m1', 25), ('m2', 0)), ('c1', ('m1', 25), ('m2', 50)),
      ...
     ('c2', ('m1', 25), ('m2', 0)), ('c2', ('m1', 25), ('m2', 25)),
     ('c2', ('m1', 50), ('m2', 0)), ('c2', ('m1', 50), ('m2', 25)), ...]
    each element in this list is also a key to the grids.
    """
    if shared_memory_info is None:
        return compute_units

    memory_names = list(shared_memory_info.keys())
    architecture_pairings = []

    for cu_idx, cu in enumerate(compute_units):
        # For this compute unit, get possible allocations from each memory
        per_memory_choices = []

        for mem in memory_names:
            partitions = shared_memory_info[mem]

            # collect unique allocations for this compute unit from all partitions
            allocations = sorted({
                partition[cu_idx]
                for partition in partitions
            })

            # tag with memory name
            per_memory_choices.append([
                (mem, alloc) for alloc in allocations
            ])

        # Cartesian product across memories
        for combo in itertools.product(*per_memory_choices):
            architecture_pairings.append((cu, *combo))

    return architecture_pairings
