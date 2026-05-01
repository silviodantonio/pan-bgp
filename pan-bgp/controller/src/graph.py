from collections import defaultdict
from heapq import heapify, heappop, heappush
import logging

# Get a logger instance
logger = logging.getLogger(__name__)

# Classes for abstracting graphs

class Node:
    def __init__(self, id: int, attributes: dict = None, adjacency_map: dict = None):
        self.id = id
        self.attributes: dict = {} if attributes is None else attributes
        self.adjacency_map: dict[Node, Edge] = {} if adjacency_map is None else adjacency_map

        logger.debug(f"initialized node {self.id}")
        logger.debug(f"Node {self.id} attributes: {self.attributes}")
        logger.debug(f"Node {self.id} adjacency_map: {self.adjacency_map}")

    def __str__(self):
        strings_list = []
        strings_list.append(f"{self.id} (deg {len(self.adjacency_map)}) :")
        edges = [(e.source.id, e.dest.id) for n, e in self.adjacency_map.items()]
        strings_list.append(str(edges))
        return " ".join(strings_list)

    def __repr__(self):
        return self.__str__()

class Edge:
    def __init__(self, source: Node, dest: Node, attributes=None):
        self.source: Node = source
        self.dest: Node = dest
        self.attributes: dict = attributes if attributes is not None else {}

# the Graph abstraction should have a minimal amount of methods.
# think of it not as a class but more as data type
class Graph:

    def __init__(self, nodes: dict = None):
        self.nodes: dict[int, Node] = {} if nodes is None else nodes

        logger.debug("Initialized a new graph")
        logger.debug(f"Graph nodes: {self.nodes}")

    def __str__(self):
        strings_list = []
        for node in self.nodes.values():
            strings_list.append(str(node))

        return "\n".join(strings_list)

    def __repr__(self):
        return self.__str__()


# Path finding functions

def find_all_paths(graph, start: Node, dest: Node, path=[]) -> list[list[Node]]:
    # Thanks to Gemini.

    current_path = path.copy()
    current_path.extend([start])

    logger.debug(f"Visiting node for AS{start.id}")

    if start == dest:
        return [current_path]

    paths = []

    for edge in start.adjacency_map.values():
        neighbor = edge.dest
        if neighbor not in current_path:
            new_paths = find_all_paths(graph, neighbor, dest, current_path)
            paths.extend(new_paths)

    return paths

## TODO: Fix all these path finding functions.

def dijkstra(graph, local_as_num, link_cost_function, link_filter_function=None):

    distance = defaultdict(lambda : None)
    distance[local_as_num] = 0

    predecessor = defaultdict(lambda : None)
    predecessor[local_as_num] = None

    priority_queue = [(0, local_as_num)]
    heapify(priority_queue)

    visited = set()

    if link_filter_function is None:
        link_filter_function = lambda link: True

    # Main algo
    while priority_queue:
        # Node with min distance
        current_distance, current_node = heappop(priority_queue)
        if current_node in visited:
            logger.debug(f"Node {current_node} already visited")
            continue
        visited.add(current_node)
        logger.debug(f"Popped from priority queue: distance: {current_distance}, node: {current_node}")

        # Get neighbors and assign a cost to each link
        neighbors_with_cost = []

        # WARN: to fix vvv
        neighbor_obj = graph
        if neighbor_obj is not None:
            neighbors_links = neighbor_obj.links.values()
            filtered_neighbors_links = filter(link_filter_function, neighbors_links)

            for link in filtered_neighbors_links:
                neighbors_with_cost.append((link.path[-1], link_cost_function(link)))

        # Update distances
        for neighbor, cost in neighbors_with_cost:
            logger.debug(f"reaching {neighbor} with cost {cost}")
            new_distance = current_distance + cost
            # if new_distance is better than previous one update it
            if (distance[neighbor] is None) or (new_distance < distance[neighbor]):
                logger.debug(f"found better cost. New: {new_distance}, old: {distance[neighbor]}")
                distance[neighbor] = new_distance
                predecessor[neighbor] = current_node
                heappush(priority_queue, (new_distance, neighbor))

    logger.debug(f"Computed MST rooted at {local_as_num}\ndistances: {distance}, predecessors: {predecessor}")
    return distance, predecessor

def least_cost_path(graph, start_as_num, dest_as_num, link_cost_function, link_filter_function) -> list[int]:

    least_cost_path = []
    cost = 0
    complete_path = []

    distance, predecessor = dijkstra(graph, start_as_num, link_cost_function, link_filter_function)
    if dest_as_num in predecessor:
        cost = distance[dest_as_num]
        current_node = dest_as_num
        while current_node != None:
            least_cost_path.append(current_node)
            current_node = predecessor[current_node]

        least_cost_path.reverse()
        logger.debug(f"Path returned from Dijkstra: {least_cost_path}")

        complete_path.append(least_cost_path[0])

        for i in range(len(least_cost_path) - 1):
            current_as_num = least_cost_path[i]
            # WARN: to fix vvv
            current_as_obj = graph.ases[current_as_num]
            next_as_num = least_cost_path[i + 1]

            filtered_links  = filter(link_filter_function, current_as_obj.links.values())
            for link in filtered_links:
                if link.path[-1] == next_as_num:
                    complete_path.extend(link.path)
                    break

        logger.debug(f"Computed \"full path\": {complete_path}")

    return complete_path, cost
