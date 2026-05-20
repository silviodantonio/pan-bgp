from threading import Thread
from threading import Lock
from time import sleep
import logging
import subprocess as sp
import ipaddress

logger = logging.getLogger(__name__)

node_singleton = None

class Path:

    def __init__(self, dest_prefix, path, metadata):
        self.dest_prefix: str = dest_prefix
        self.path: list[int] = path
        self.metadata: dict[str] = metadata

    def __str__(self):
        return f"{self.dest_prefix}: {self.path} ({self.metadata})"

    def __repr__(self):
        return self.__str__()

class Node:

    def __init__(self, asn: int, attached_prefixes: list[str], 
                 as_paths: dict[str, Path], locator: str):

        self.asn: int = asn
        self.attached_prefixes: list[str] = attached_prefixes
        self.locator: str = locator

        # Considering one path per prefix
        self.as_paths: dict[str, Path] = as_paths
        self.as_paths_lock = Lock()


    def update_as_paths(self, as_paths: list[Path]):

        self.as_paths_lock.acquire()

        for path_obj in as_paths:
            dest_prefix = path_obj.dest_prefix
            self.as_paths[dest_prefix] = path_obj

        self.as_paths_lock.release()

    def get_as_paths(self) -> dict[str, list[Path]]:
        self.as_paths_lock.acquire()
        paths_dict = self.as_paths
        self.as_paths_lock.release()
        return paths_dict

    def __str__(self):
        strings_list = []
        strings_list.append(f"Node: AS{self.asn}, locator: ({self.locator})")
        strings_list.append(f"Attached prefixes ({len(self.attached_prefixes)}): {self.attached_prefixes}")
        as_paths = self.get_as_paths()
        strings_list.append(f"AS Paths ({len(as_paths)}): {list(as_paths.values())}")
        return (", ").join(strings_list)

    def __repr__(self):
        return self.__str__()


class PrefixPoller(Thread):

    """ Periodically ping addresses for getting average RTT values"""
    # This thread does not work! The implementation is wrong

    def __init__(self, sleep_time):
        super().__init__()
        self.sleep_time = sleep_time

    def _get_avg_rtt(self, prefix: str, ping_count:int, ping_deadline) -> float:

        avg_rtt_time = 0
        address = prefix.split('/')[0]

        ping_command = ["ping",
                   f"{address}", 
                   "-c", f"{ping_count}",
                   "-w", f"{ping_deadline}",
                   "-q"]

        try:
            completed_proc = sp.run(ping_command, check=True, capture_output=True, text=True)
            command_out = completed_proc.stdout
            command_out.split(" ")
            rtt_times = command_out[-2]
            rtt_times.split("/")
            avg_rtt_time = float(rtt_times[1])

        except sp.CalledProcessError as proc_err:
            logger.warning(f"Couldn't interact with ping: {proc_err}")
            logger.debug(f"Ping command out: {command_out}")

        finally:
            return avg_rtt_time

    def run(self):

        while True:

            node_singleton.as_paths_lock.acquire()

            # WARN: Pinging prefixes is wrong. I need exact addresses
            try:
                for dest_prefix, paths_list in node_singleton.as_paths.items():
                    avg_rtt = self._get_avg_rtt(dest_prefix, 3, 3)
                    logger.debug(f"RTT for {dest_prefix}: {avg_rtt}")
                    if avg_rtt != 0:
                        for path in paths_list:
                            if "bestpath" in path.metadata:
                                path.metadata["rtt"] = avg_rtt
            except Exception as e:
                logger.warn(f"Raised an exception while getting RTT. {e}")
            finally:
                node_singleton.as_paths_lock.release()

            sleep(self.sleep_time)

def build_sid(locator, func_number):

    # This function is most likey not robust enough
    # and or/buggy. However, it does the job well
    # enough for what i need

    logger.debug(f"Got locator {locator} and function number {func_number}")

    locator_prefix_len = locator.split("/")[1]

    logger.debug(f"Locator prefix len: {locator_prefix_len}")

    # How many blocks i have for the subnet?
    prefix_blocks = int(locator_prefix_len) // 16
    subnet_blocks = 8 - prefix_blocks - 1

    # Move "up" for the required number of blocks
    logger.debug(f"Moving up the function number of {subnet_blocks} blocks")
    func_addr_value = func_number * (2**(16*subnet_blocks))

    locator_network = ipaddress.IPv6Network(locator)
    locator_addr = locator_network.network_address

    logger.debug("Computing new SID")
    sid = str(locator_addr + func_addr_value)

    logger.debug(f"Built SID: {sid}")
    return sid

def interface_for(dest_prefix):

    try:
        # search dest_prefix in ipv4 routes first
        command = "ip route list"

        completed_proc = sp.run(command,
                                shell=True,
                                check=True,
                                capture_output=True,
                                text=True)

        routes_list = completed_proc.stdout.split("\n")

        for route in routes_list:
            logger.debug(f"Finding interface on: {route}")
            route = route.split(" ")
            if dest_prefix == route[0]:
                iface_index = route.index("dev") + 1
                if iface_index != -1:
                    iface = route[iface_index]
                    logger.debug(f"found interface for {dest_prefix}: {iface}")
                    return iface

        # search between ipv6 routes
        command = "ip -6 route list"

        completed_proc = sp.run(command,
                                shell=True,
                                check=True, 
                                capture_output=True,
                                text=True)

        routes_list = completed_proc.stdout.split("\n")

        for route in routes_list:
            logger.debug(f"Finding interface on: {route}")
            route = route.split(" ")
            if dest_prefix == route[0]:
                iface_index = route.index("dev") + 1
                if iface_index != -1:
                    iface = route[iface_index]
                    logger.debug(f"found interface for {dest_prefix}: {iface}")
                    return iface

    except sp.CalledProcessError as proc_err:
        logger.critical(f"Couldn't extract outbound interface: {proc_err}")
        return None


def install_srv6_path(dest_prefix: str, path: list[tuple[int, str]]):

    # path is a list of tuples.
    # each tuple contains an ASN and its SRv6 locator

    # remove "myself" from path
    path = path[1:]

    # using replace:
    # - if the route is new is added
    # - if an old route was already there it is updated
    command = ["ip -6 route replace", dest_prefix, "encap seg6 mode encap", "segs"]

    # build and add segment list to command
    segment_list = []

    if len(path) > 1:
        for node_asn, node_locator in path[:-1]:
            # End behavior (defined by me with function code 1)
            segment_list.append(build_sid(node_locator, 0x1))

    last_node_asn, last_node_locator = path[-1]
    # End.DT6 behavior (defined by me with function code 100)
    segment_list.append(build_sid(last_node_locator, 0x100))

    logger.debug(f"Constructed segment list: {segment_list}")
    command.append(",".join(segment_list))

    # get outbound interface and add it to command
    _, first_hop_locator = path[0]
    outbound_iface = interface_for(first_hop_locator)
    logger.debug(f"Using iface {outbound_iface} as outbound interface")
    command.append(f"dev {outbound_iface}")

    try:
        logging.debug("Installing a new SRv6 route")
        sp.run(" ".join(command),
               shell=True,
               check=True, 
               capture_output=True, 
               text=True)

    except sp.CalledProcessError as proc_err:
        logger.critical(f"Couldn't install route: {proc_err}")
