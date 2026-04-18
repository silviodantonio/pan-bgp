import sys
import logging

from configuration import Configuration
import socket_interface
import messaging
import core

if __name__=='__main__':

    try:
        configuration = Configuration("/etc/panbgp/panbgp.conf")
    except Exception as e:
        raise e
        sys.exit(1)

    logger = logging.getLogger(__name__)

    controller_address = configuration.controller["address"]
    controller_port = configuration.controller["port"]
    messager = messaging.Messager(controller_address, controller_port)

    logger.info("Sending node info for the first time")
    messager.send_as_info()

    # Periodically get info about paths and their RTT
    logger.info("Starting services for getting data about AS paths")
    paths_updater = core.PathsUpdater(2)
    paths_updater.start()

    # prefix_poller = core.PrefixPoller(2)
    # prefix_poller.start()

    logger.info("Starting AS paths beaconing thread")
    beacon_thread = messaging.ASPathBeaconingThread(messager, 5)
    beacon_thread.start()

    # I would like not to pass controller info here
    local_socket_interface_addr = configuration.interactive_interface["address"]
    local_socket_interface_port = configuration.interactive_interface["port"]

    logger.info("Starting local socket interface")
    local_socket_interface_thread = socket_interface.LocalSocketInterfaceThread(
            local_socket_interface_addr,
            local_socket_interface_port,
            messager)
    local_socket_interface_thread.start()

    try:
        messager.request_path("192.0.2.0/30", "trusted_paths", 5)
    except Exception as e: 
        logger.debug(f"An exception occurred while requesting paths: {e}")
