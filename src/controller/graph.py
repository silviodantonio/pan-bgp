from collections import deque
import sys
import logging

# Get a logger instance
logger = logging.getLogger(__name__)

# Logger configuration
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
file_handler = logging.FileHandler("/var/log/pangbp.log")
file_handler.setFormatter(formatter)

# Tell logger to output to file.
logger.addHandler(file_handler)


class Node:

    def __init__(self):
        self.id = None
        # store neighbors
        self.neighbors = set()

class ASNode(Node):

    def __init__(self):
        super().__init__()
        self.controlled = False
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
                neighbor_nodes_list.append(neighbor.get(neighbor.id))
            return_str += f"{node_id}: {neighbor_nodes_list}\n"
        return return_str

class ASGraph(Graph):

    def __init__(self):
        super().__init__()
        self.prefix_as_table = {}

    def add_node(self, node: ASNode):
        super().add_node(node)
        for prefix in node.prefixes:
            self.prefix_as_table[prefix] = node.id
        logger.debug("New AS node in graph")

    def find_all_paths(self, start_as: ASNode, dest_as: ASNode, path=[]):
    # Thanks to Gemini.
    # WARN: not fully understood however,
    # Being recursive might also work extremely poorly on large graphs.

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
