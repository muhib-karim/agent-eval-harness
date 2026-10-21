import heapq


def topo_sort(graph):
    deps = {}
    for node, ds in graph.items():
        s = deps.setdefault(node, set())
        for d in ds:
            s.add(d)
    for ds in list(deps.values()):
        for d in ds:
            if d not in deps:
                deps[d] = set()

    indegree = {}
    dependents = {n: [] for n in deps}
    for node, ds in deps.items():
        indegree[node] = len(ds)
        for d in ds:
            dependents[d].append(node)

    heap = [n for n, c in indegree.items() if c == 0]
    heapq.heapify(heap)
    result = []
    while heap:
        n = heapq.heappop(heap)
        result.append(n)
        for m in dependents[n]:
            indegree[m] -= 1
            if indegree[m] == 0:
                heapq.heappush(heap, m)

    if len(result) != len(deps):
        raise ValueError("graph contains a cycle")
    return result
