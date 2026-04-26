from collections import defaultdict
from heapq import heapify, heappop, heappush
import logging
from threading import Lock


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

def cost_rtt(link) -> float:

    cost = 9999
    rtt_link = link.metadata.get('rtt')
    if rtt_link is not None:
        cost = rtt_link
    return cost

def filter_trusted_links(link):
    trusted = False
    dest_as = singleton_network_graph.ases.get(link.path[-1])
    if dest_as is not None:
        if dest_as.trusted and len(link.path) == 1:
            trusted = True
    return trusted

def filter_links_rtt(link):
    if "rtt" in link.metadata:
        return True
    else:
        return False


class Link():

    # This class is basically a BGP route with some metadata
    def __init__(self, dest_prefix: str, path: list[int], metadata: dict):
        self.dest_prefix: str = dest_prefix
        self.path: list[int] = path
        self.metadata: dict = metadata

    def __str__(self):
        strings_list = []

        strings_list.append(f"Path: {str(self.dest_prefix)}")
        strings_list.append(str(self.path))
        strings_list.append(str(self.metadata))

        return ", ".join(strings_list)

    def __repr__(self):
        return self.__str__()


class AS():

    def __init__(self, as_number, identity_prefix):

        self.number: int = as_number
        self.identity_prefix: str = identity_prefix
        self.trusted = True
        self.announced_prefixes: list[str] = []
        self.links: dict[str, Link] = {}
        self.links_lock = Lock()

    def announces_prefix(self, prefix: str) -> None:
        if is_owner(self.number, prefix):
            self.announced_prefixes.append(prefix)
        else:
            self.trusted = False

    def update_links(self, links: list[Link]) -> None:
        self.links_lock.acquire()
        for link in links:
            self.links[link.dest_prefix] = link
        self.links_lock.release()

    def get_links(self):
        self.links_lock.acquire()
        links = self.links.values()
        self.links_lock.release()
        return links

    def __str__(self):
        strings_list = []

        trusted_status = "trusted" if self.trusted else "untrusted"
        strings_list.append(f"AS{self.number}: {self.identity_prefix} {trusted_status}")

        prefixes_str = f"Announced prefixes ({len(self.announced_prefixes)}): {self.announced_prefixes}"
        strings_list.append(prefixes_str)

        links_str = f"Links ({len(self.links)}): {list(self.links.values())}"
        strings_list.append(links_str)

        return "\n".join(strings_list)

    def __repr__(self):
        return self.__str__()


class NetworkGraph():

    def __init__(self):
        self.ases: dict[int, AS] = {}
        self.prefix_table: dict[str, AS] = {}

    def add_as(self, new_as: AS):
        if new_as.number in self.ases:
            raise ValueError(f"AS{new_as.number} is already in NetworkGraph")
        else:
            self.ases[new_as.number] = new_as
            for prefix in new_as.announced_prefixes:
                self.prefix_table[prefix] = new_as
            logger.debug("New AS node in graph")


    def find_all_paths(self, start_as: AS, dest_as: AS, link_filter, path=[]) -> list[list[AS]]:
        # Thanks to Gemini.

        current_path = path.copy()
        current_path.extend([start_as])

        logger.debug(f"Visiting AS{start_as.number}")

        if start_as == dest_as:
            return [current_path]

        paths = []

        filtered_links: Link = filter(link_filter, start_as.get_links())
        neighbor_ases = []
        for link in filtered_links:
            neighbor_asn = link.path[-1]
            neighbor_as_obj = self.ases.get(neighbor_asn)
            if (neighbor_as_obj is not None and 
                neighbor_as_obj not in neighbor_ases):
                neighbor_ases.append(neighbor_as_obj)

        neighbors_nums = [int(as_obj.number) for as_obj in neighbor_ases]
        logger.debug(f"Extracted neighbors: {neighbors_nums}")

        for neighbor_as in neighbor_ases:
            if neighbor_as not in current_path:
                new_paths = self.find_all_paths(
                    neighbor_as, dest_as, link_filter, current_path)
                paths.extend(new_paths)

        return paths

    def trusted_paths(self, start_asn: int, dest_asn: int):

        start_as = self.ases[start_asn]
        dest_as = self.ases[dest_asn]
        return self.find_all_paths(start_as, dest_as, filter_trusted_links)


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
