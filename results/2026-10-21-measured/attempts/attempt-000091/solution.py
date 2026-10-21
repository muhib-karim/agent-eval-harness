import heapq


def topo_sort(graph) -> list:
    """
    Topologically sort a dependency graph.

    graph: mapping node -> iterable of nodes it depends on.
    Returns a list containing every node exactly once, with every node's
    dependencies appearing before it. Among nodes that are simultaneously
    ready, the smallest is emitted first, yielding the lexicographically
    smallest valid ordering.

    Raises ValueError if the graph contains a cycle (including self-loops).
    Does not mutate the input. Iterative (no recursion), so very long
    chains are handled without hitting the recursion limit.
    """
    # Build our own structures so the input is never mutated.
    # dependents[d] = set of nodes that depend on d
    # indegree[n] = number of distinct dependencies of n
    dependents = {}
    indegree = {}

    def ensure(node):
        if node not in indegree:
            indegree[node] = 0
            dependents[node] = set()

    for node, deps in graph.items():
        ensure(node)
        # Deduplicate dependencies: duplicates count once.
        seen = set()
        for dep in deps:
            if dep in seen:
                continue
            seen.add(dep)
            ensure(dep)
            if node not in dependents[dep]:
                dependents[dep].add(node)
                indegree[node] += 1

    # Kahn's algorithm with a min-heap for smallest-first selection.
    ready = [node for node, deg in indegree.items() if deg == 0]
    heapq.heapify(ready)

    result = []
    while ready:
        node = heapq.heappop(ready)
        result.append(node)
        for child in dependents[node]:
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(ready, child)

    if len(result) != len(indegree):
        raise ValueError("graph contains a cycle")

    return result
