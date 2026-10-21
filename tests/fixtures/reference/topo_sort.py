import heapq


def topo_sort(graph):
    deps = {}
    for node, requires in graph.items():
        deps.setdefault(node, set()).update(requires)
        for dep in deps[node]:
            deps.setdefault(dep, set())
    dependents = {node: [] for node in deps}
    remaining = {}
    for node, requires in deps.items():
        remaining[node] = len(requires)
        for dep in requires:
            dependents[dep].append(node)
    ready = [node for node, count in remaining.items() if count == 0]
    heapq.heapify(ready)
    order = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for child in dependents[node]:
            remaining[child] -= 1
            if remaining[child] == 0:
                heapq.heappush(ready, child)
    if len(order) != len(deps):
        raise ValueError("graph contains a cycle")
    return order
