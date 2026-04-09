from collections import deque

import utils

# Get a logger instance
logger = utils.get_logger(__name__)


# Dummy RPKI prefix validator
def is_owner(as_number, prefix) -> bool:
    # TODO: implement
    return True

def filter_trusted_links(link):
    trusted = False
    dest_as = singleton_network_graph.ases.get(link.dest)
    if (dest_as is not None) and dest_as.trusted and (len(link.path) == 1):
        trusted = True
    logger.debug(f"Link: {link.source} {link} is trusted? {trusted}")
    return trusted

class Link():

    # Not using AS object since destination could be
    # a non-controlled AS, for which AS objects are not created.
    def __init__(self, source: int, dest: int, path: list[int]):
        self.source: int = source
        self.dest: int = dest

        # List will be empty for directly connected peers.
        # Otherwise, it will contain the AS path extracted from the controller.
        self.path: list[int] = path

    def __str__(self):
        link_elem_list = []
        # link_elem_list.append(str(self.source))
        for hop in self.path:
            link_elem_list.append(str(hop))
        # link_elem_list.append(str(self.dest))
        return ' '.join(link_elem_list)


class AS():

    def __init__(self, as_number):
        self.number: int = as_number

        # Maybe useless. The fact that the object exists
        # means that the AS is controlled.
        self.controlled = True
        self.trusted = True

        self.prefixes: set[str] = set()
        self.links: dict[int, Link] = {}

    def add_prefix(self, prefix: str) -> None:
        if is_owner(self.number, prefix):
            self.prefixes.add(prefix)
        else:
            self.trusted = False

    def add_links(self, links: list[Link]) -> None:

        for link in links:
            # replace known links if different from previously known
            if link.dest in self.links:
                if self.links.get(link.dest) != link:
                    self.links[link.dest] = link
                    logger.debug(f'Updating link for {link.dest}: {link}')
            # otherwise just add it to the list
            else:
                logger.debug(f'Adding new link for {link.dest}: {link}')
                self.links[link.dest] = link

    def __str__(self):
        links = [str(link) for link in self.links.values()]
        links_str = ', '.join(links)
        return f"""AS{self.number:}:
            Trusted: {self.trusted}
            Prefixes [{len(self.prefixes)}]: {str(self.prefixes)}
            Links [{len(self.links)}]: {links_str}"""


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

        current_path = path.copy()
        current_path.extend([start_as])

        if start_as == dest_as:
            return [current_path]

        # Get trusted peers
        start_as_obj = self.ases.get(start_as)
        trusted_links = filter(filter_trusted_links, start_as_obj.links.values())
        trusted_peers: int = [link.dest for link in trusted_links]

        paths = []
        for trusted_peer in trusted_peers:
            if trusted_peer not in current_path:
                new_paths = self._find_trusted_paths(
                    trusted_peer, dest_as, current_path)
                paths.extend(new_paths)

        return paths

    def trusted_paths(self, start_as: int, dest_as: int) -> list[list[int]]:
        # Here there was a BFS graph check.
        return self._find_trusted_paths(start_as, dest_as, [])

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
        ases = [str(as_obj) for as_obj in self.ases.values()]
        return '\n\n'.join(ases)

singleton_network_graph = NetworkGraph()
