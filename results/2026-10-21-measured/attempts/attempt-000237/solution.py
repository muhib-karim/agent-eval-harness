def topo_sort(graph):
    """
    Topologically sort a directed acyclic graph (DAG).

    Args:
        graph: Dict mapping each node to an iterable of nodes it depends on.
               Returns nodes in order such that dependencies come before dependents.
               When multiple nodes are ready, emit the smallest first.

    Returns:
        List of all nodes in topologically sorted order.

    Raises:
        ValueError: If the graph contains a cycle.
    """
    if not graph:
        return []

    # Build a complete graph including nodes that only appear as dependencies
    all_nodes = set(graph.keys())
    for dependencies in graph.values():
        all_nodes.update(dependencies)

    # Build in-degree map and adjacency list (reverse dependencies)
    in_degree = {node: 0 for node in all_nodes}
    dependents = {node: set() for node in all_nodes}

    for node, deps in graph.items():
        # Use a set to handle duplicate dependencies
        unique_deps = set(deps)
        in_degree[node] = len(unique_deps)
        for dep in unique_deps:
            dependents[dep].add(node)

    # Find all nodes with no dependencies (in_degree == 0)
    # Use a sorted list as a min-heap (keeping it sorted for lexicographic order)
    ready = sorted([node for node in all_nodes if in_degree[node] == 0])

    result = []

    # Process nodes using Kahn's algorithm
    while ready:
        # Take the smallest node (lexicographically first)
        current = ready.pop(0)
        result.append(current)

        # Process all nodes that depend on current
        for dependent in sorted(dependents[current]):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                # Insert in sorted order to maintain lexicographic ordering
                # Using binary search for efficiency with large graphs
                import bisect
                bisect.insort(ready, dependent)

    # Check if all nodes were processed (no cycles)
    if len(result) != len(all_nodes):
        raise ValueError("Graph contains a cycle")

    return result
