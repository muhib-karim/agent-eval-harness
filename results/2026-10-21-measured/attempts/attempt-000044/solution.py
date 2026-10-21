import heapq


def topo_sort(graph) -> list:
    """Return nodes ordered so dependencies come before dependents.

    graph maps each node to an iterable of nodes it depends on.
    Among nodes ready at the same time, the smallest is emitted first,
    yielding the lexicographically smallest valid order.
    Raises ValueError if the graph contains a cycle.
    """
    # Build a private copy of the structure; never mutate the input.
    deps = {}        # node -> set of unique dependencies
    dependents = {}  # node -> list of nodes that depend on it

    for node, ds in graph.items():
        dep_set = set(ds)  # duplicates count once
        deps[node] = dep_set
        dependents.setdefault(node, [])
        for d in dep_set:
            dependents.setdefault(d, []).append(node)
            if d not in deps:
                deps.setdefault(d, set())

    # Nodes appearing only as dependencies get an empty dependency set.
    for node in dependents:
        deps.setdefault(node, set())

    indegree = {node: len(ds) for node, ds in deps.items()}

    heap = [node for node, deg in indegree.items() if deg == 0]
    heapq.heapify(heap)

    result = []
    while heap:
        node = heapq.heappop(heap)
        result.append(node)
        for child in dependents.get(node, ()):
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(heap, child)

    if len(result) != len(indegree):
        raise ValueError("graph contains a cycle")

    return result
