import heapq


def topo_sort(graph):
    deps = {}
    for node, ds in graph.items():
        s = set(ds)
        deps[node] = s
    # include nodes that appear only as dependencies
    for node, s in list(deps.items()):
        for d in s:
            if d not in deps:
                deps[d] = set()

    dependents = {node: [] for node in deps}
    indegree = {}
    for node, s in deps.items():
        indegree[node] = len(s)
        for d in s:
            dependents[d].append(node)

    heap = [n for n, k in indegree.items() if k == 0]
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
