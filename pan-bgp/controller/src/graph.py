from collections import deque
import sys
from itertools import permutations

import utils

# Get a logger instance
logger = utils.get_logger(__name__)

class Node:

    def __init__(self):
        self.id = None
        # store neighbors
        self.neighbors = set()

class AS(Node):

    def __init__(self):
        super().__init__()
        self.controlled = False
        self.trusted = False
        self.prefixes = set()


class Graph:

    def __init__(self):
        # id: object
        self.nodes = {}

    def add_node(self, node: Node):
        if node.id in self.nodes:
            raise ValueError('Node with same id already exists')
        else:
            self.nodes[node.id] = node

    def del_node(self, node_idtorm):

        node_torm = self.nodes.get(node_idtorm)
        if node_torm is None:
            raise ValueError('No such node')

        # remove it as neighbor from all other nodes
        for node_id, node in self.nodes.items():
            if node_torm in node.neighbors:
                node.neighbors.remove(node_torm)

        del self.nodes[node_idtorm]

    def add_edge(self, start_node_id, end_node_id):
        start_node = self.nodes.get(start_node_id)
        if start_node is None:
            raise ValueError(f"No node with id {start_node_id}")

        end_node = self.nodes.get(end_node_id)
        if start_node is None:
            raise ValueError(f"No node with id {start_node_id}")

        # Undirected graph
        start_node.neighbors.add(end_node)
        end_node.neighbors.add(start_node)

    def del_edge(self, start_node_id, end_node_id):
        start_node = self.nodes.get(start_node_id)
        if start_node is None:
            raise ValueError(f"No node with id {start_node_id}")

        end_node = self.nodes.get(end_node_id)
        if start_node is None:
            raise ValueError(f"No node with id {start_node_id}")

        # Undirected graph
        start_node.neighbors.remove(end_node)
        end_node.neighbors.remove(start_node)

    def __str__(self):
        return_str = ''
        for node_id, node in self.nodes.items():
            neighbor_nodes_list = []
            for neighbor in node.neighbors:
                neighbor_nodes_list.append(neighbor.id)
            return_str += f"{node_id}: {neighbor_nodes_list}\n"
        return return_str

class ASGraph(Graph):

    def __init__(self):
        super().__init__()
        self.prefix_as_table = {}

    def add_node(self, node: AS):
        super().add_node(node)
        for prefix in node.prefixes:
            self.prefix_as_table[prefix] = node.id
        logger.debug("New AS node in graph")

    def find_all_paths(self, start_as: AS, dest_as: AS, path=[]) -> list[list[AS]]:
    # Thanks to Gemini.
    # WARN: not fully understood and
    # being recursive might also work extremely poorly on large graphs.

        current_path = path.copy()
        current_path.extend([start_as])

        if start_as == dest_as:
            return [current_path]

        paths = []
        for neighbor_as in start_as.neighbors:
            if neighbor_as not in current_path:
                new_paths = self.find_all_paths(neighbor_as, dest_as, current_path)
                paths.extend(new_paths)

        return paths

    def _find_trusted_paths(self, start_as: AS, dest_as: AS, path=[]) -> list[list[AS]]:
    # Thanks to Gemini part II (this code is copied from find_all_paths)

        as_trusted_peers = [as_peer for as_peer in start_as.neighbors if as_peer.trusted]

        current_path = path.copy()
        current_path.extend([start_as])

        if start_as == dest_as:
            return [current_path]

        paths = []
        for as_trusted_peer in as_trusted_peers:
            if as_trusted_peer not in current_path:
                new_paths = self.find_all_paths(as_trusted_peer, dest_as, current_path)
                paths.extend(new_paths)

        return paths

    def find_trusted_paths(self, start_as:AS, dest_as: AS) -> list[list[AS]]:
        return self._find_trudted_paths(start_as, dest_as, [])

    def reachable_nodes_from(self, start_as: AS) -> set[AS]:
        # use bfs to explore the graph component to which start_as belongs
        logger.debug("Computing reachable nodes")

        visited = set()
        nodes_deque = deque([start_as])

        while len(nodes_deque) != 0:
            current_node = nodes_deque.popleft()
            if current_node not in visited:
                visited.add(current_node)
                for neighbor in current_node.neighbors:
                    nodes_deque.append(neighbor)

        logger.debug("Done computing reachable nodes")

        return visited

    def get_components(self) -> list[set[AS]]:
        logger.debug("Computing graph components")
        # Get all components of the topology graph

        graph_nodes = set()
        for as_number, as_obj in self.nodes.items():
            graph_nodes.add(as_obj)

        components = []

        # while some node is left
        while len(graph_nodes) != 0:
            # choose randomly a node
            starting_node = graph_nodes.pop()
            graph_nodes.add(starting_node)

            # explore the connected component
            logging.debug("Exploring a new component")
            connected_component = self.reachable_nodes_from(starting_node)
            components.append(connected_component)
            # remove the nodes of the component from the nodes left to visit
            graph_nodes = graph_nodes.difference(connected_component)

        logger.debug("Done computing graph components")

        return components

    # Probably this function is not really needed. The approach of connecting
    # components is wrong
    def connect_components(self, l_set: set[AS], r_set: set[AS]):

        logger.debug("Connecting components")

        uncontrolled_l_nodes = [node for node in l_set if not node.controlled]
        uncontrolled_r_nodes = [node for node in r_set if not node.controlled]

        for l_node in uncontrolled_l_nodes:
            for r_node in uncontrolled_r_nodes:
                self.add_edge(l_node.id, r_node.id)

        logger.debug("Done connecting components")


    def fully_connect(self, nodes):
        # Given a set of notes, adds edges between them in order connect them
        # in a full mesh (clique)

        # In principle, since this is an undirected graph i need to do
        # half loop for building a full mesh. For now won't optimize for that

        for current_node in nodes:
            for new_neighbor in nodes:
                if new_neighbor is not current_node:
                    self.add_edge(current_node, new_neighbor)

    def trusted_midpoints_sequences(self, start_as: AS, end_as: AS, num=None):

        logger.debug("Attempting to compute sequence of trusted midponts")

        trusted_ases = []

        for node_id, node_obj in self.nodes.items():
            if node_obj.trusted:
                trusted_ases.append(node_obj)

        logger.debug("Got list of trusted ASes")

        # Since i can assume an AS can reach any other AS, that means
        # that i can think of them as connected by a full mesh.
        # That means that computing a path mans computing a permutation of
        # ASes of desired length

        # remove source_as and end_as
        if start_as in trusted_ases:
            trusted_ases.remove(start_as)
        if end_as in trusted_ases:
            trusted_ases.remove(end_as)
        logger.debug("Removed start AS and end AS from trusted list")

        if len(trusted_ases) == 0:
            return []

        if num is not None:
            # check that i have enough trusted AS to compute midpoints
            if len(trusted_ases) < num:
                return []
        else:
            # num was none, so use all trusted ASes
            num = len(trusted_ases)

        logger.debug(f"Computing sequences of {num} trusted midponts")
        # computing all sequences of trusted ASes
        paths = [deque(permutation) for permutation in permutations(trusted_ases, r=num)]

        logger.debug("Computed all permutations")

        for path in paths:
            path.appendleft(start_as)
            path.append(end_as)

        logger.debug("Added back start_as and end_as to permutations")

        return paths
