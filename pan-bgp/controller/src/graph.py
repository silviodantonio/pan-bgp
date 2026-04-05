from collections import deque

import utils

# Get a logger instance
logger = utils.get_logger(__name__)


# Dummy RPKI prefix validator
def is_owner(as_number, prefix) -> bool:
    # TODO: implement
    return True

class Link():

    # Not using AS object since destination could be
    # a non-controlled AS, for which AS objects are not created.
    def __init__(self, source: int, dest: int, path: list[int]):
        self.source: int = source
        self.dest: int = dest

        # List will be empty for directly connected peers.
        # Otherwise, it will contain the AS path extracted from the controller.
        self.path: list[int]


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

        self.links: dict[int, Link] = {}

    def announces_prefix(self, prefix: str) -> None:
        if is_owner(self.number, prefix):
            self.prefixes.add(prefix)
        else:
            self.trusted = False

    def add_as_paths(self, paths_dict) -> None:

        for dest_as, as_path in paths_dict.items():
            known_as_path = self.as_paths.get(dest_as)
            if known_as_path is None or known_as_path != as_path:
                self.links[dest_as] = as_path

    def add_links(self, links: list[Link]) -> None:

        for link in links:
            # filter out potentially unwanted links
            if link.source == self.number:
                # if link to dest already exists
                currently_known_link = self.links.get(link.dest)
                if currently_known_link is not None:
                    # replace if different
                    if currently_known_link != link:
                        self.links[link.dest] = link


class NetworkGraph():

    def __init__(self):
        self.ases: dict[int, AS] = {}
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


    def _find_trusted_paths(self, start_as: int, dest_as: int, path=[]) -> list[list[int]]:
        # Thanks to Gemini part II (this code is copied from find_all_paths)
        # I don't fully understand what's happening here and what is being passed during
        # the recursion.

        # get trusted_peers
        trusted_peers = []
        start_as_obj = self.ases.get(start_as)
        for link_dest, link_path in start_as_obj.links.items():
            if link_dest in self.ases and link_path == []:
                trusted_peers.append(link_dest)

        current_path = path.copy()
        current_path.extend([start_as])

        if start_as == dest_as:
            return [current_path]

        paths = []
        for trusted_peer in trusted_peers:
            if trusted_peer not in current_path:
                new_paths = self._find_trusted_paths(
                    trusted_peer, dest_as, current_path)
                paths.extend(new_paths)

        return paths

    def trusted_paths(self, start_as: int, dest_as: int) -> list[list[int]]:

        start_as_component = self.bfs(start_as)
        if dest_as in start_as_component:
            return self._find_trusted_paths(start_as, dest_as, [])
        else:
            return [[]]

    def bfs(self, start_as: int) -> set[int]:

        # use bfs to explore the graph component to which start_as belongs
        logger.debug(f"Computing reachable nodes from AS{start_as}")

        visited = set()
        nodes_deque = deque([start_as])

        # while i have some nodes to visit
        while len(nodes_deque) != 0:
            # get the current node
            current_node = nodes_deque.popleft()
            if current_node not in visited:
                # if it's a new node
                visited.add(current_node)
                # add to visit all directly connected nodes
                current_as_obj = self.ases.get(current_node)
                for link_dest, link_path in current_as_obj.links.items():
                    if link_path == []:
                        nodes_deque.append(link_dest)

        return visited

    def __str__(self):
        adjacency_dictionary_list = {}
        for as_number, as_obj in self.ases.items():
            as_peers = [as_peer for as_peer in as_obj.peers]
            adjacency_dictionary_list[as_number] = as_peers
        return str(adjacency_dictionary_list)
