import heapq
from collections import defaultdict


def topo_sort(graph) -> list:
    dependents = defaultdict(list)
    indegree = {}

    for node, dependencies in graph.items():
        indegree.setdefault(node, 0)
        for dependency in set(dependencies):
            indegree.setdefault(dependency, 0)
            dependents[dependency].append(node)
            indegree[node] += 1

    ready = [node for node, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)

    order = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)

        for dependent in dependents[node]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)

    if len(order) != len(indegree):
        raise ValueError("graph contains a cycle")

    return order
