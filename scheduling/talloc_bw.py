from scheduling.graph import Node


def assign_time_bwu(
    node: Node,
    memory_name,
    curr_schedule: dict[Node, float],
    clocks: dict[str, float],
    # everybody in chunked_bwu has higher priority already
    chunked_bwu # list of dicts containing: 
    # 'einsum': str
    # 'start': float
    # 'end': float
    # 'bwu': float
):
    """
    Allocates time for [node] and its dependencies, 
    respecting the current schedule, clocks, and bandwidth utilization.
    """
    if memory_name is None:
        raise ValueError("How did we end up here?")

    if node.flag == Node.DONE:
        return

    if node.flag == Node.VISITED:
        raise ValueError("Cycle in graph")

    node.flag = Node.VISITED
    
    for dep in node.dependencies:
        assign_time_bwu(dep, memory_name, curr_schedule, clocks, chunked_bwu)

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
    
    while not done:
        # if memory_ops_remaining != total_mem_ops:
        #     print("We are in a chunk smaller than the full Einsum!", chunked_bwu, node)
        if memory_ops_remaining == 0:  # if no memory ops, skip the loop
            chunk_end = chunk_start + latency_remaining
            done = True
            break
        
        executing_tasks = [t for t in chunked_bwu if t['start'] <= chunk_start and t['end'] > chunk_start]
        avail_bwu = 1 - sum(t['bwu'] for t in executing_tasks)

        if avail_bwu == 0:
            print("If we had not considered bwu, we would have violated a constraint here!", curr_schedule)
            chunk_start = max(chunk_start, min([t['end'] for t in executing_tasks]))
        else:
            actual_usage = min(desired_bwu, avail_bwu)
            
            # the latency if the available bandwidth remained constant for the full computation

            actual_mem_lat = (desired_bwu / actual_usage) * (memory_ops_remaining * lat_per_mem_op)
            actual_latency = max(actual_mem_lat, latency_remaining)
            # lat_remaining = (node.total_latency * (memory_ops_remaining / total_mem_ops))
            chunk_end = min([t['end'] for t in executing_tasks] + [chunk_start + actual_latency])

            chunked_bwu.append({
                'einsum': node.einsum_name,
                'start': chunk_start,
                'end': chunk_end,
                'bwu': actual_usage,
            })

            if (actual_latency == chunk_end - chunk_start):
                done = True
            
            # set up for next chunk
            memory_ops_remaining = memory_ops_remaining - ((actual_usage/desired_bwu) * (total_mem_ops / node.total_latency) * (chunk_end - chunk_start))
            latency_remaining = node.total_latency * (memory_ops_remaining / total_mem_ops)

            chunk_start = chunk_end

    node.total_latency = chunk_end - start

    curr_schedule[node] = start
    clocks[node.compute_assignment] = curr_schedule[node] + node.total_latency
    node.flag = Node.DONE
    if log(curr_schedule):
        print(node, '\t', chunked_bwu)


def log(curr_schedule: dict[Node, float]):
    return False
    e0 = any(
        node.einsum_name == "E0" and node.compute_assignment == "fast"
        for node in curr_schedule)
    e1 = any(
        node.einsum_name == "E1" and node.compute_assignment == "slow"
        for node in curr_schedule)
    e2 = any(
        node.einsum_name == "E2" and node.compute_assignment == "fast"
        for node in curr_schedule)
    e3 = any(
        node.einsum_name == "E3" and node.compute_assignment == "slow"
        for node in curr_schedule)
    e4 = any(
        node.einsum_name == "E4" and node.compute_assignment == "slow"
        for node in curr_schedule)

    return e0 and e1 and e2 and e3 and e4


