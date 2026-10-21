import heapq


def topo_sort(graph) -> list:
    # Snapshot dependencies (each iterable consumed exactly once), dedupe them.
    deps = {}
    for node, ds in graph.items():
        deps[node] = set(ds)

    # Include nodes that appear only as dependencies.
    all_nodes = set(deps)
    for ds in list(deps.values()):
        all_nodes.update(ds)
    for n in all_nodes:
        if n not in deps:
            deps[n] = set()

    # Build reverse edges and in-degree counts (number of unmet dependencies).
    dependents = {n: [] for n in all_nodes}
    remaining = {}
    for node, ds in deps.items():
        remaining[node] = len(ds)
        for d in ds:
            dependents[d].append(node)

    heap = [n for n, c in remaining.items() if c == 0]
    heapq.heapify(heap)

    result = []
    while heap:
        n = heapq.heappop(heap)
        result.append(n)
        for m in dependents[n]:
            remaining[m] -= 1
            if remaining[m] == 0:
                heapq.heappush(heap, m)

    if len(result) != len(all_nodes):
        raise ValueError("graph contains a cycle")
    return result
