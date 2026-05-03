from collections import defaultdict
from heapq import heapify, heappop, heappush
from itertools import count
import copy
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
    def __init__(self, source: Node, dest: Node, cost=None, attributes=None):
        self.source: Node = source
        self.dest: Node = dest
        self.cost = cost
        self.attributes: dict = attributes if attributes is not None else {}

# the Graph abstraction should have a minimal amount of methods.
# think of it not as a class but more as data type
class Graph:

    def __init__(self, nodes: dict = None):
        self.nodes: dict[int, Node] = {} if nodes is None else nodes

        logger.debug("Initialized a new graph")
        logger.debug(f"Graph nodes: {self.nodes}")

    def remove_node(self, node: Node):

        # remove edges that lead to node to be deleted
        for node_id, node_obj in self.nodes.items():
            if node_obj != node:
                adj_map = node_obj.adjacency_map.copy()
                for adj_node, _ in adj_map.items():
                    if adj_node.id == node.id:
                        del node_obj.adjacency_map[node]

        # remove the requested node
        del self.nodes[node.id]

    def remove_edge(self, start: Node, end: Node):
        edge_to_remove = start.adjacency_map.get(end)
        if edge_to_remove is not None:
            del start.adjacency_map[end]

    def __str__(self):
        strings_list = []
        for node in self.nodes.values():
            strings_list.append(str(node))

        return "\n".join(strings_list)

    def __repr__(self):
        return self.__str__()


# Path finding functions

def find_all_paths(graph: Graph, start: Node, dest: Node, path=[]) -> list[list[Node]]:
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


def dijkstra(graph: Graph, start: Node):

    distance = defaultdict(lambda : None)
    distance[start.id] = 0

    predecessor = defaultdict(lambda : None)
    predecessor[start] = None

    # counter is just a counter.
    # it is used for breaking ties when there are elements
    # with the same priority in the priority queue.
    counter = count()
    priority_queue = [(0, next(counter), start)]
    heapify(priority_queue)

    visited = set()

    # Main algo
    while priority_queue:

        # Get Node with min distance, discarding the counter
        current_distance, _, current_node = heappop(priority_queue)
        if current_node in visited:
            logger.debug(f"Node {current_node} already visited")
            continue

        visited.add(current_node)
        logger.debug(f"Popped from priority queue: distance: {current_distance}, node: {current_node}")

        edges = current_node.adjacency_map.values()

        # Update distances
        for edge in edges:

            neighbor = edge.dest
            new_distance = current_distance + edge.cost
            logger.debug(f"reaching {neighbor} with cost {edge.cost}")
            # if new_distance is better than previous one update it
            if (distance[neighbor.id] is None) or (new_distance < distance[neighbor.id]):
                logger.debug(f"found better cost. New: {new_distance}, old: {distance[neighbor.id]}")
                distance[neighbor.id] = new_distance
                predecessor[neighbor] = current_node
                heappush(priority_queue, (new_distance, next(counter), neighbor))

    logger.debug(f"Computed MST rooted at {start.id}\ndistances: {distance}, predecessors: {predecessor}")
    return distance, predecessor


def least_cost_path(graph: Graph, start: Node, dest: Node) -> list[Node]:

    least_cost_path = []
    cost = 0

    distance, predecessor = dijkstra(graph, start)
    if dest in predecessor:
        cost = distance[dest]
        current_node = dest
        while current_node != None:
            least_cost_path.append(current_node)
            current_node = predecessor[current_node]

        least_cost_path.reverse()
        logger.debug(f"Path returned from Dijkstra: {least_cost_path}")

    return least_cost_path, cost

def least_cost_paths(graph: Graph, start: Node, dest: Node, paths_num: int):

    # Yen's algorithm for finding K (paths_num) least cost paht
    # Implementation based on the pseudocode found in the Wikipedia article

    found_paths = []

    # compute first least cost path
    dijkstra_path, _ = least_cost_path(graph, start, dest)
    found_paths.append([node.id for node in dijkstra_path])

    counter = count()
    candidate_paths = []
    heapify(candidate_paths)

    # compute the others k-1 paths
    for k in range(paths_num - 1):
        working_path = found_paths[-1]
        for i, node_id in enumerate(working_path[:-1]):

            working_graph = copy.deepcopy(graph)

            spur_node = working_graph.nodes[node_id]
            # root path includes spur node
            root_path = working_path[:i+1]
            logger.debug(f"root_path: {root_path}")
            logger.debug(f"spur_node: {spur_node}")

            # Check for paths that have the same root path.
            # remove previously used edges from spur node to next node.
            for prev_found_path in found_paths:
                prev_root_path = prev_found_path[:i+1]
                if root_path == prev_root_path:
                    next_to_spur_node = working_graph.nodes[prev_found_path[i+1]]
                    logger.debug(f"Removing edge ({spur_node.id}, {next_to_spur_node.id}) from graph")
                    working_graph.remove_edge(spur_node, next_to_spur_node)

            # remove each root_path node from graph, except spur_node
            for root_node_id in root_path[:-1]:
                node_to_remove = working_graph.nodes[root_node_id]
                logger.debug(f"Removing node {node_to_remove.id} from graph")
                working_graph.remove_node(node_to_remove)

            # compute a new spur_path (starts form spur_node) using Dijkstra
            dest_node = working_graph.nodes[dest.id]
            spur_path, _ = least_cost_path(working_graph, spur_node, dest_node)
            if len(spur_path) != 0:
                new_path = root_path[:-1] + [node.id for node in spur_path]
                heappush(candidate_paths, (len(new_path), next(counter), new_path))

        if len(candidate_paths) == 0:
            logger.debug("Couldn't find more candidate paths")
            break
        else:
            path_len, _, found_path = heappop(candidate_paths)
            logger.debug(f"Found new path: {found_path}")
            found_paths.append(found_path)

    # convert found paths from sequence of ids to sequence of nodes
    converted_paths = []
    for path in found_paths:
        converted_path = [graph.nodes[node_id] for node_id in path]
        converted_paths.append(converted_path)

    return converted_paths
