import heapq


def topo_sort(graph) -> list:
    # Collect all nodes (keys and dependencies) without mutating input
    deps_map = {}
    all_nodes = set()

    for node, deps in graph.items():
        all_nodes.add(node)
        unique_deps = set()
        for d in deps:
            unique_deps.add(d)
            all_nodes.add(d)
        deps_map[node] = unique_deps

    # Ensure every node has an entry in deps_map (nodes only appearing as deps)
    for node in all_nodes:
        if node not in deps_map:
            deps_map[node] = set()

    # Build reverse adjacency: dep -> list of nodes that depend on it
    dependents = {node: [] for node in all_nodes}
    in_degree = {node: 0 for node in all_nodes}

    for node, deps in deps_map.items():
        in_degree[node] = len(deps)
        for d in deps:
            dependents[d].append(node)

    # Initialize heap with nodes having in_degree 0
    heap = [node for node in all_nodes if in_degree[node] == 0]
    heapq.heapify(heap)

    result = []
    while heap:
        node = heapq.heappop(heap)
        result.append(node)
        for dependent in dependents[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                heapq.heappush(heap, dependent)

    if len(result) != len(all_nodes):
        raise ValueError("Graph has a cycle")

    return result
