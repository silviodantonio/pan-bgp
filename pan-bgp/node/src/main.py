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

    # Most likely this can be done better: i would like not to pass the controller
    socket_interface_addr = configuration.interactive_interface["address"]
    socket_interface_port = configuration.interactive_interface["port"]
    socket_interface.start(socket_interface_addr, socket_interface_port, controller)

    try:
        controller.request_path("192.0.2.0/30", "none", 5)
    except Exception as e: 
        logger.debug(f"An exception occurred while sending AS info: {e}")
