"""Random spanning trees over the cells of the text, as the order in which
they reach each cell: the paths that burn's fire and laseretch's laser follow."""
from __future__ import annotations

from tpy import int32, Own, copy

from engine import Terminal, randint


def _visited_from(term: Terminal, start: int32) -> Own[list[bool]]:
    visited: list[bool] = []
    for _ in range(len(term.chars)):
        visited.append(False)
    visited[start] = True
    return visited


def prims_order(term: Terminal, start: int32) -> Own[list[int32]]:
    """Prim's algorithm with random choices over the cells of the text: the
    order in which a randomly grown tree reaches each cell, starting at `start`."""
    visited = _visited_from(term, start)
    order = [start]
    edge = [start]
    while edge:
        current = edge.pop(randint(0, len(edge) - 1))
        unvisited = unvisited_neighbors(term, current, visited)
        if not unvisited:
            continue
        linked = unvisited.pop(randint(0, len(unvisited) - 1))
        visited[linked] = True
        order.append(linked)
        if unvisited:
            edge.append(current)
        onward = unvisited_neighbors(term, linked, visited)
        if onward:
            edge.append(linked)
    return order


def unvisited_neighbors(term: Terminal, char_id: int32, visited: list[bool]) -> Own[list[int32]]:
    found: list[int32] = []
    for neighbor in term.neighbors(char_id):
        coord = copy(term.chars[neighbor].input_coord)
        if not visited[neighbor] and term.canvas.coord_is_in_text(coord):
            found.append(neighbor)
    return found


def recursive_backtracker_order(term: Terminal, start: int32) -> Own[list[int32]]:
    """A depth-first random walk that backs up when it gets stuck: long,
    winding runs rather than Prim's spreading front."""
    visited = _visited_from(term, start)
    order = [start]
    stack = [start]
    current = start
    while stack:
        unvisited = unvisited_neighbors(term, current, visited)
        if unvisited:
            linked = unvisited[randint(0, len(unvisited) - 1)]
            visited[linked] = True
            order.append(linked)
            stack.append(linked)
            current = linked
        else:
            stack.pop()
            if stack:
                current = stack[len(stack) - 1]
    return order
