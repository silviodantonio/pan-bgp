import sys
import logging

from configuration import Configuration
import socket_interface
import controller as ctrl

if __name__=='__main__':

    try:
        configuration = Configuration("/etc/panbgp/panbgp.conf")
    except Exception as e:
        raise e
        sys.exit(1)

    logger = logging.getLogger(__name__)

    controller_address = configuration.controller["address"]
    controller_port = configuration.controller["port"]
    controller = ctrl.Controller(controller_address, controller_port)

    controller.send_as_info()

    as_path_beaconing_thread = ctrl.ASPathBeaconingThread(controller, 5)
    # Immediately sends an update and then repeats every 5s
    as_path_beaconing_thread.start()

    # I would like not to pass controller info here
    local_socket_interface_addr = configuration.interactive_interface["address"]
    local_socket_interface_port = configuration.interactive_interface["port"]

    local_socket_interface_thread = socket_interface.LocalSocketInterfaceThread(
            local_socket_interface_addr,
            local_socket_interface_port,
            controller)
    local_socket_interface_thread.start()

    try:
        controller.request_path("192.0.2.0/30", "trusted_paths", 5)
    except Exception as e: 
        logger.debug(f"An exception occurred while requesting paths: {e}")
