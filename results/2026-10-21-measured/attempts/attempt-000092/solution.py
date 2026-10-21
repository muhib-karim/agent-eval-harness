import heapq


def topo_sort(graph) -> list:
    """
    Topologically sort a dependency graph.

    graph: mapping node -> iterable of nodes it depends on.
    Returns a list of all nodes (including those appearing only as
    dependencies), with every dependency before its dependents. Among
    nodes that are simultaneously ready, the smallest is emitted first,
    yielding the lexicographically smallest valid ordering.

    Raises ValueError if the graph contains a cycle (including self-loops).
    The input is not mutated.
    """
    # Build dependency sets (deduplicated) without touching the input.
    deps = {}
    for node, dependencies in graph.items():
        s = deps.setdefault(node, set())
        for d in dependencies:
            s.add(d)
            # Ensure dependency-only nodes exist in our structure.
            deps.setdefault(d, set())

    # In-degree = number of distinct dependencies; dependents = reverse edges.
    indegree = {}
    dependents = {node: [] for node in deps}
    for node, s in deps.items():
        indegree[node] = len(s)
        for d in s:
            dependents[d].append(node)

    # Min-heap of all nodes with no outstanding dependencies.
    ready = [node for node, deg in indegree.items() if deg == 0]
    heapq.heapify(ready)

    result = []
    while ready:
        node = heapq.heappop(ready)
        result.append(node)
        for dep in dependents[node]:
            indegree[dep] -= 1
            if indegree[dep] == 0:
                heapq.heappush(ready, dep)

    if len(result) != len(deps):
        raise ValueError("graph contains a cycle")

    return result
