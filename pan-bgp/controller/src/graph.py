from collections import deque

import utils

# Get a logger instance
logger = utils.get_logger(__name__)


def is_owner(as_number, prefix) -> bool:
    # TODO: implement
    return True


class AS():

    def __init__(self, as_number, peers: list[int]):
        self.number: int = as_number
        self.controlled = True
        self.trusted = True
        self.prefixes: set[str] = set()
        self.as_paths: list[int] = {}

        self.peers: set[int] = set()
        for peer in peers:
            self.peers.add(peer)

    def announces_prefix(self, prefix: str):
        if is_owner(self.number, prefix):
            self.prefixes.add(prefix)
        else:
            self.trusted = False


class NetworkGraph():

    def __init__(self):
        self.ases: dict[str, AS] = {}
        self.prefix_table: dict[str, AS] = {}

    def add_as(self, new_as: AS):
        if new_as.number in self.ases:
            raise ValueError(f"AS{new_as.number} is already in NetworkGraph")
        else:
            self.ases[new_as.number] = new_as
            for prefix in new_as.prefixes:
                self.prefix_table[prefix] = new_as
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
                new_paths = self.find_all_paths(
                    neighbor_as, dest_as, current_path)
                paths.extend(new_paths)

        return paths

    def _find_trusted_paths(self, start_as: AS, dest_as: AS, path=[]) -> list[list[AS]]:
        # Thanks to Gemini part II (this code is copied from find_all_paths)
        # I don't fully understand what's happening here and what is being passed during
        # the recursion.

        controlled_as_peers = [self.ases(as_peer_id) for as_peer_id in start_as.peers]
        as_trusted_peers = [as_peer for as_peer in controlled_as_peers if as_peer.trusted]

        current_path = path.copy()
        current_path.extend([start_as])

        if start_as == dest_as:
            return [current_path]

        paths = []
        for as_trusted_peer in as_trusted_peers:
            if as_trusted_peer not in current_path:
                new_paths = self._find_trusted_paths(
                    as_trusted_peer, dest_as, current_path)
                paths.extend(new_paths)

        return paths

    def trusted_paths(self, start_as: AS, dest_as: AS) -> list[list[AS]]:

        start_as_component = self.bfs(start_as)
        if dest_as in start_as_component:
            return self._find_trusted_paths(start_as, dest_as, [])
        else:
            return [[]]

    def bfs(self, start_as: AS) -> set[AS]:
        # use bfs to explore the graph component to which start_as belongs
        logger.debug(f"Computing reachable nodes from AS{start_as.number}")

        visited = set()
        nodes_deque = deque([start_as])

        # while i have some nodes to visit
        while len(nodes_deque) != 0:
            # get the current node
            current_node = nodes_deque.popleft()
            if current_node not in visited:
                # if it's a new node
                visited.add(current_node)
                for neighbor in current_node.neighbors:
                    nodes_deque.append(neighbor)

        return visited

    def __str__(self):
        adjacency_dictionary_list = {}
        for as_number, as_obj in self.ases.items():
            as_peers = [as_peer for as_peer in as_obj.peers]
            adjacency_dictionary_list[as_number] = as_peers
        return str(adjacency_dictionary_list)
