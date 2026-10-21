import heapq


def topo_sort(graph):
    deps = {}
    for node, ds in graph.items():
        s = deps.setdefault(node, set())
        for d in ds:
            s.add(d)
    # include nodes that appear only as dependencies
    for node in list(deps):
        for d in deps[node]:
            if d not in deps:
                deps[d] = set()

    dependents = {node: [] for node in deps}
    indeg = {}
    for node, s in deps.items():
        indeg[node] = len(s)
        for d in s:
            dependents[d].append(node)

    heap = [n for n, k in indeg.items() if k == 0]
    heapq.heapify(heap)
    result = []
    while heap:
        n = heapq.heappop(heap)
        result.append(n)
        for m in dependents[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                heapq.heappush(heap, m)

    if len(result) != len(deps):
        raise ValueError("graph contains a cycle")
    return result
