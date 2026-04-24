from threading import Thread
from threading import Lock
from time import sleep
import logging
import subprocess as sp

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
                 as_paths: dict[str, Path], identity_prefix: str):

        self.asn: int = asn
        self.attached_prefixes: list[str] = attached_prefixes
        self.identity_prefix: str = identity_prefix

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
        strings_list.append(f"Node: AS{self.asn} ({self.identity_prefix})")
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
