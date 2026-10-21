"""Topological sort with deterministic (lexicographically smallest) ordering."""

import heapq


def topo_sort(graph) -> list:
    """Return all nodes of `graph` ordered so dependencies precede dependents.

    `graph` maps each node to an iterable of the nodes it depends on.
    Among nodes that are ready at the same time, the smallest is emitted first.
    Raises ValueError if the graph contains a cycle (including self-loops).
    The input is not mutated.
    """
    # Collect deduplicated dependencies for every node, including nodes that
    # only appear as dependencies.
    deps = {}
    for node, node_deps in graph.items():
        deps.setdefault(node, set()).update(node_deps)
    for node in list(deps):
        for d in deps[node]:
            if d not in deps:
                deps[d] = set()

    # Build reverse adjacency (dependency -> dependents) and in-degrees.
    dependents = {node: [] for node in deps}
    indegree = {}
    for node, node_deps in deps.items():
        indegree[node] = len(node_deps)
        for d in node_deps:
            dependents[d].append(node)

    heap = [node for node, deg in indegree.items() if deg == 0]
    heapq.heapify(heap)

    result = []
    while heap:
        node = heapq.heappop(heap)
        result.append(node)
        for nxt in dependents[node]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                heapq.heappush(heap, nxt)

    if len(result) != len(deps):
        raise ValueError("graph contains a cycle")
    return result
