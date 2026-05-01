from scheduling.graph import Node


def assign_time_shared_mem(
    node: Node,
    memory_name,
    curr_schedule: dict[Node, float],
    clocks: dict[str, float],
    # everybody in chunked_bwu has higher priority already
    chunked_bwu, # list of dicts containing: 
    # 'einsum': str
    # 'start': float
    # 'end': float
    # 'bwu': float
    # 'mem_usage': dict(str, float)
):
    """
    Allocates time for [node] and its dependencies, 
    respecting the current schedule, clocks, and bandwidth utilization.
    """
   
    
    if memory_name is None:
        raise ValueError("How did we end up here?")
    if len(node.compute_assignment) <= 1:
        raise ValueError("How did we end up here?")

    if node.flag == Node.DONE:
        return
    if node.flag == Node.VISITED:
        raise ValueError("Cycle in graph")

    node.flag = Node.VISITED
    
    for dep in node.dependencies:
        assign_time_shared_mem(dep, memory_name, curr_schedule, clocks, chunked_bwu)

    # start time
    start = max(
        (curr_schedule[dep] + dep.total_latency for dep in node.dependencies),
        default=0
    )

    # info for this full einsum
    latency_remaining = node.total_latency
    memory_latency = node.latencies_per_unit[memory_name]
    desired_bwu = memory_latency / node.total_latency
    
    total_mem_ops = sum(count for (memory, op), count in node.actions.items() if memory == memory_name)
    lat_per_mem_op = memory_latency / total_mem_ops
    memory_ops_remaining = total_mem_ops


    chunk_start = start
    done = False
    bwu_ok = False
    mem_cap_ok = False
    node_mem_max_capacity = node.compute_assignment[1:]
    
    while not (done or (bwu_ok and mem_cap_ok)):
        if np.isclose(memory_ops_remaining, 0):  # if no memory ops, skip the loop
            print("broke out of loop early!!")
            chunk_end = chunk_start + latency_remaining
            done = True
            break
        
        executing_tasks = [t for t in chunked_bwu if t['start'] <= chunk_start and t['end'] > chunk_start]

        # check memory capacity
        used_capacities = {}
        for t in executing_tasks:
            for k, v in t["mem_usage"].items():
                used_capacities[k] = used_capacities.get(k, 0) + v

        mem_cap_ok = True
        mem_cap = {}
        print("sched:", curr_schedule, used_capacities, executing_tasks, chunked_bwu, chunk_start, node, id(chunked_bwu))
        for mem, capacity in node_mem_max_capacity:
            if 100 - used_capacities.get(mem, 0) < capacity:
                memory_ops_remaining = total_mem_ops
                chunk_start = max(chunk_start, min([t['end'] for t in executing_tasks]))
                start = chunk_start
                mem_cap_ok = False
                break
            mem_cap[mem] = capacity

        print("mem cap ok:", mem_cap_ok)
        if not mem_cap_ok:
            continue
        
        # check memory bandwidth
        avail_bwu = 1 - sum(t['bwu'] for t in executing_tasks)
        if np.isclose(avail_bwu, 0):
            new_chunk_start = min([t['end'] for t in executing_tasks])
            assert(new_chunk_start > chunk_start)
            chunk_start = new_chunk_start
            bwu_ok = False
            continue
        
        actual_usage = min(desired_bwu, avail_bwu)
        
        # the latency if the available bandwidth remained constant for the full computation
        actual_mem_lat = (desired_bwu / actual_usage) * (memory_ops_remaining * lat_per_mem_op)
        actual_latency = max(actual_mem_lat, latency_remaining)
        # lat_remaining = (node.total_latency * (memory_ops_remaining / total_mem_ops))
        chunk_end = min(
            [chunk_start + actual_latency] +
            [t['end'] for t in executing_tasks] +
            [t['start'] for t in chunked_bwu if t['start'] > chunk_start and t['start'] < chunk_start + actual_latency]
        )
        
        if (np.isclose(actual_latency, chunk_end - chunk_start)):
            bwu_ok = True
        else:
            bwu_ok = False
        print("bwu_ok:", bwu_ok)
        chunked_bwu.append({
            'einsum': node.einsum_name,
            'start': chunk_start,
            'end': chunk_end,
            'bwu': actual_usage,
            'mem_usage': mem_cap
        })
        
        # set up for next chunk
        memory_ops_remaining = memory_ops_remaining - ((actual_usage/desired_bwu) * (total_mem_ops / node.total_latency) * (chunk_end - chunk_start))
        latency_remaining = node.total_latency * (memory_ops_remaining / total_mem_ops)
        chunk_start = chunk_end

    node.total_latency = chunk_end - start

    curr_schedule[node] = start
    clocks[node.compute_assignment] = curr_schedule[node] + node.total_latency
    node.flag = Node.DONE
