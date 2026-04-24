import sys
import logging

from threading import Thread
from time import sleep

from configuration import Configurator
import socket_interface
import messaging
import core
import frr

class PathsUpdaterService(Thread):

    def __init__(self, node, refresh_rate: int):
        super().__init__()
        self.node = node
        self.refresh_rate = refresh_rate

    def run(self):

        try:
            while True:
                as_paths_list = frr.get_as_paths()
                if len(as_paths_list) != 0:
                    logger.info("Got new AS paths. Updating node info")
                    self.node.update_as_paths(as_paths_list)
                    logger.debug(self.node)
                else:
                    logger.debug("No new as paths in RIB")

                sleep(self.refresh_rate)
        except Exception as e:
            logger.error(f"An exception was raised when attempting to refresh AS paths. {e}")

if __name__ == '__main__':

    try:
        configuration = Configurator("/etc/panbgp/panbgp.conf")
    except Exception as e:
        raise e
        sys.exit(1)

    logger = logging.getLogger(__name__)

    logger.info("Initializing Node object")
    initial_as_paths = frr.get_as_paths()
    initial_as_paths_dict = {}
    for as_path in initial_as_paths:
        initial_as_paths_dict[as_path.dest_prefix] = as_path

    core.node_singleton = core.Node(
            frr.get_asn(),
            frr.get_attached_prefixes(),
            initial_as_paths_dict,
            configuration.main["identity_prefix"])

    logger.debug(core.node_singleton)

    logger.info("Initializing messager for talking to controller")
    messager = messaging.Messager(configuration.main, core.node_singleton)

    logger.info("Sending first message to controller")
    messager.send_as_info()

    logger.info("Starting service: paths updater service")
    rib_refresh_rate = configuration.main["rib_refresh_rate"]
    paths_updater_service = PathsUpdaterService(core.node_singleton, rib_refresh_rate)
    paths_updater_service.start()

    logger.info("Starting service: controller beaconing")
    beaconing_rate = configuration.main["beaconing_rate"]
    messager.start_path_beaconing(beaconing_rate)

    local_socket_interface_addr = configuration.interactive_interface["address"]
    local_socket_interface_port = configuration.interactive_interface["port"]

    logger.info("Starting local socket interface")
    local_socket_interface_thread = socket_interface.LocalSocketInterfaceThread(
            local_socket_interface_addr,
            local_socket_interface_port,
            messager)
    local_socket_interface_thread.start()

    logger.info("Startup done")

    # This if for testing purposes

    # try:
    #     messager.request_path("192.0.2.0/30", "trusted_paths", 5)
    # except Exception as e: 
    #     logger.debug(f"An exception occurred while requesting paths: {e}")
