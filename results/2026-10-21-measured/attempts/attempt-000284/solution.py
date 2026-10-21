import heapq


def topo_sort(graph) -> list:
    """Return the lexicographically smallest dependency-first ordering."""
    indegree = {}
    dependents = {}

    for node, dependencies in graph.items():
        indegree.setdefault(node, 0)
        seen = set()

        for dependency in dependencies:
            if dependency in seen:
                continue
            seen.add(dependency)

            indegree.setdefault(dependency, 0)
            indegree[node] += 1
            dependents.setdefault(dependency, []).append(node)

    ready = [node for node, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)

    result = []
    while ready:
        node = heapq.heappop(ready)
        result.append(node)

        for dependent in dependents.get(node, ()):
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)

    if len(result) != len(indegree):
        raise ValueError("graph contains a cycle")

    return result
