import pytest
from solution import topo_sort


def test_empty_graph() -> None:
    assert topo_sort({}) == []


def test_single_node_without_dependencies() -> None:
    assert topo_sort({"a": []}) == ["a"]


def test_chain_puts_dependencies_first() -> None:
    assert topo_sort({"c": ["b"], "b": ["a"], "a": []}) == ["a", "b", "c"]


def test_diamond_is_lexicographically_smallest() -> None:
    graph = {"d": ["b", "c"], "c": ["a"], "b": ["a"], "a": []}
    assert topo_sort(graph) == ["a", "b", "c", "d"]


def test_ready_set_prefers_smallest_not_insertion_order() -> None:
    graph = {"z": [], "m": [], "a": ["z"]}
    assert topo_sort(graph) == ["m", "z", "a"]


def test_dependency_only_nodes_are_included() -> None:
    assert topo_sort({"app": ["lib", "util"]}) == ["lib", "util", "app"]


def test_integer_nodes_and_duplicate_dependencies() -> None:
    assert topo_sort({3: [1, 1, 2], 2: [1], 10: []}) == [1, 2, 3, 10]


def test_cycle_raises() -> None:
    with pytest.raises(ValueError):
        topo_sort({"a": ["b"], "b": ["c"], "c": ["a"]})


def test_self_loop_raises() -> None:
    with pytest.raises(ValueError):
        topo_sort({"a": ["a"]})


def test_cycle_behind_valid_prefix_raises() -> None:
    with pytest.raises(ValueError):
        topo_sort({"ok": [], "x": ["ok", "y"], "y": ["x"]})


def test_input_is_not_mutated_and_iterables_accepted() -> None:
    graph = {"b": ("a",), "c": {"a", "b"}, "a": []}
    snapshot = {key: list(value) for key, value in graph.items()}
    assert topo_sort(graph) == ["a", "b", "c"]
    assert {key: list(value) for key, value in graph.items()} == snapshot


def test_long_chain_without_recursion_limit() -> None:
    n = 10_000
    graph = {i: [i - 1] for i in range(1, n)}
    assert topo_sort(graph) == list(range(n))
