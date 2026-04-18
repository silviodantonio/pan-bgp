from collections import deque, defaultdict
from heapq import heapify, heappop, heappush
import logging


# Get a logger instance
logger = logging.getLogger(__name__)


# Dummy RPKI prefix validator
def is_owner(as_number, prefix) -> bool:
    # TODO: implement
    return True

def cost_untrusted_AS(link) -> int:

    cost = 0
    for as_ in link.path:
        as_obj = singleton_network_graph.ases.get(as_)
        if (as_obj is None) or (as_obj.trusted == False):
            cost += 1

    return cost

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
        # TODO: (?) if i want to use this i need to adapt it. 
        # It needs to use the link abstraction.

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

    def dijkstra(self, local_as_num, link_cost_function, link_filter_function=None) -> list[list[int]]:

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

            neighbor_obj = singleton_network_graph.ases.get(current_node)
            if neighbor_obj is not None:
                neighbors_links = neighbor_obj.links.values()
                filtered_neighbors_links = filter(link_filter_function, neighbors_links)

                for link in filtered_neighbors_links:
                    neighbors_with_cost.append((link.dest, link_cost_function(link)))

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

    def least_cost_path(self, start_as_num, dest_as_num, link_cost_function, link_filter_function) -> list[int]:

        least_cost_path = []
        cost = 0
        complete_path = []

        distance, predecessor = self.dijkstra(start_as_num, link_cost_function, link_filter_function)
        if dest_as_num in predecessor:
            cost = distance[dest_as_num]
            current_node = dest_as_num
            while current_node != None:
                least_cost_path.append(current_node)
                current_node = predecessor[current_node]

            least_cost_path.reverse()
            logger.debug(f"Path returend from Dijkstra: {least_cost_path}")

            # Fill "gaps" in the returned path
            as_num = least_cost_path[0]
            complete_path.append(as_num)
            for i in range(len(least_cost_path)-1):
                # Append paths of links as_num to next_as_num
                next_as_num = least_cost_path[i+1]

                as_obj = singleton_network_graph.ases[as_num]
                link_to_next = as_obj.links[next_as_num]

                complete_path.extend(link_to_next.path)
                as_num = next_as_num

            logger.debug(f"Computed \"full path\": {complete_path}")

        return complete_path, cost


    def __str__(self):
        ases = [str(as_obj) for as_obj in self.ases.values()]
        return '\n\n'.join(ases)

singleton_network_graph = NetworkGraph()
