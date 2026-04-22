import accelforge as af


def trunc(s):
    return s.rsplit("/", 1)[-1].rsplit(".yaml", 1)[0]


def af_map(arch, workload):
    spec = af.Spec.from_yaml(
        arch,
        workload
    )
    spec.mapper.metrics = af.Metrics.LATENCY | af.Metrics.ENERGY 
    mapping = spec.map_workload_to_arch()
    return mapping


def process_mapping(arch, workload, mapping):
    filename = trunc(arch) + "-" + trunc(workload)
    with open("images/" + filename + ".svg", "w") as f:
        f.write(mapping.render())

    actions = mapping.actions(per_einsum=True, per_component=True)
    latency = mapping.latency(per_einsum=True)
    
    total_reads = 0
    total_writes = 0
    for (einsum, lat) in latency.items():
        component = "MainMemory"
        reads = actions[(einsum, component, "read")]
        writes = actions[(einsum, component, "write")]
        total_reads += reads
        total_writes += writes

    rw = total_reads + total_writes
    latency = mapping.latency()

    mem_actions = {}
    for (op, mem, action), value in actions.items():
        if action != "compute" and mem == "MainMemory":   # ignore compute entries
            key = (op, mem)
            mem_actions[key] = mem_actions.get(key, 0.0) + value
    
    return {
        'mapping': mapping,
        'total reads': total_reads,
        'total write': total_writes,
        'total r+w': rw,
        'latency': latency,
        '(r+w)/latency': rw / latency,
        'bw util': (rw/latency) / 6.4e9, # todo ugly i am hardcoded
        'mem summary': mem_actions
    }


def af_grid(einsums: list[str], units: list[str], einsum_path, arch_path):
    """
    [einsum_path] and [arch_path] are functions which take an einsum 
    or arch name respectively, and return the path to the appropriate 
    .yaml file.
    """
    grid = {}
    i = 0
    for sub_arch in units:
        for einsum in einsums:
            i += 1
            print("Getting cell " + str(i) + " of " + str(len(einsums) * len(units)))
            grid[(sub_arch, einsum)] = af_map(
                arch_path(sub_arch),
                einsum_path(einsum)
            )
    # Accelforge might return multiple mappings. Pick the best one.
    best_grid_lats = {}
    best_grid_mems = {}
    best_grid_maps = {}
    for cell, m in grid.items():
        best = m[0]
        for i in range(len(m)):
            if m[i].latency() < best.latency():
                best = m[i]

        best_grid_lats[cell] = best.latency()
    
        
        actions = best.actions(per_einsum=True, per_component=True)
        latency = best.latency(per_einsum=True)

        total_reads = 0
        total_writes = 0
        for (einsum, lat) in latency.items():
            component = "MainMemory"
            reads = actions[(einsum, component, "read")]
            writes = actions[(einsum, component, "write")]
            total_reads += reads
            total_writes += writes
        rw = total_reads + total_writes
        best_grid_mems[cell] = rw

        best_grid_maps[cell] = best
    
    return best_grid_lats, best_grid_mems, best_grid_maps
