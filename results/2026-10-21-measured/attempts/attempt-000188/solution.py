import heapq
from collections import defaultdict


def topo_sort(graph) -> list:
    # Collect all nodes, including those only appearing as dependencies
    all_nodes = set()
    deps = {}  # node -> set of dependencies (deduplicated)

    for node, dependencies in graph.items():
        all_nodes.add(node)
        dep_set = set()
        for dep in dependencies:
            dep_set.add(dep)
            all_nodes.add(dep)
        deps[node] = dep_set

    # Ensure every node has an entry in deps (nodes only appearing as deps)
    for node in all_nodes:
        if node not in deps:
            deps[node] = set()

    # Build reverse adjacency: dependency -> list of dependents
    dependents = defaultdict(list)
    in_degree = {}

    for node in all_nodes:
        in_degree[node] = len(deps[node])
        for dep in deps[node]:
            dependents[dep].append(node)

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
        raise ValueError("Graph contains a cycle")

    return result
