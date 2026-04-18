from threading import Thread
from threading import Lock
from time import sleep
import logging
import subprocess as sp

import frr

logger = logging.getLogger(__name__)

class Node:

    def __init__(self):
        self.local_asn = frr.local_asn()
        self.bgp_peers = frr.bgp_peers_asn()
        self.attached_prefixes = frr.get_attached_prefixes()

        # init paths
        self.as_paths_lock = Lock()
        self.as_paths = {}
        # self.add_paths(frr.get_as_paths())


    def add_paths(self, as_paths: list[frr.Path]):
        self.as_paths_lock.acquire()

        for path_obj in as_paths:
            dest_prefix = path_obj.dest_prefix
            if dest_prefix not in self.as_paths:
                self.as_paths[dest_prefix] = [path_obj]
            else:
                self.as_paths[dest_prefix].append(path_obj)

        self.as_paths_lock.release()

    def replace_paths(self, as_paths: list[frr.Path]):
        self.as_paths_lock.acquire()

        self.as_paths = {}
        for path_obj in as_paths:
            dest_prefix = path_obj.dest_prefix
            if dest_prefix not in self.as_paths:
                self.as_paths[dest_prefix] = [path_obj]
            else:
                self.as_paths[dest_prefix].append(path_obj)

        self.as_paths_lock.release()

        logger.info("Replaced AS paths")

    def get_paths(self) -> dict[str, list[frr.Path]]:
        self.as_paths_lock.acquire()
        paths_dict = self.as_paths
        self.as_paths_lock.release()
        return paths_dict


node_singleton = Node()


class PathsUpdater(Thread):

    def __init__(self, refresh_rate: int):
        super().__init__()
        self.refresh_rate = refresh_rate

    def run(self):

        # Here i can add a nice timing mechanism
        try:
            while True:
                logger.info("Checking for new AS paths")
                as_paths = frr.get_as_paths()
                if len(as_paths) != 0:
                    logging.info(f"Got {len(as_paths)} new AS paths. Updating node info")
                    logger.debug(f"New AS Paths: {as_paths}")
                    node_singleton.replace_paths(as_paths)

                sleep(self.refresh_rate)
        except Exception as e:
            logger.error("An exception was raised when attempting to get updated paths.")
            logger.debug(f"{e}")


class PrefixPoller(Thread):

    def __init__(self, sleep_time):
        super().__init__()
        self.sleep_time = sleep_time

    def _get_avg_rtt(prefix: str, ping_count:int, ping_deadline) -> float:

        avg_rtt_time = 0

        ping_command = ["ping",
                   f"{prefix}", 
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
            logging.warn(f"Couldn't interact with ping: {proc_err}")

        finally:
            return avg_rtt_time

    def run(self):

        while True:

            node_singleton.as_paths_lock.acquire()


            # I think something is going wrong here
            for dest_prefix, paths_list in node_singleton.as_paths.items():
                avg_rtt = self._get_avg_rtt(dest_prefix, 3, 3)
                logger.debug(f"RTT for {dest_prefix}: {avg_rtt}")
                if avg_rtt != 0:
                    for path in paths_list:
                        if "bestpath" in path.metadata:
                            path.metadata["rtt"] = avg_rtt

            node_singleton.as_paths_lock.release()

            sleep(self.sleep_time)
