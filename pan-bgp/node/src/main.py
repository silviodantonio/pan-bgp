import logging
from time import sleep # temporary import until concurrency issues are fixed

import grpc

import vtysh_iface
import controller_pb2
import controller_pb2_grpc
import socket_interface
import controller_interface

# Get logger and configure it
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
file_handler = logging.FileHandler("/var/log/pangbp.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


if __name__=='__main__':

    controller = controller_interface.Controller()

    # Here should go a "attempt to reconnect loop"
    try:
        controller.send_as_info()
    except Exception as e: 
        logger.debug(f"An exception occurred while sending AS info: {e}")
    # is this enough to induce an endless loop?
    socket_interface.start()
    # sleep(5)
    try:
        controller.request_path('192.0.2.0/30', 'none', 5)
    except Exception as e: 
        logger.debug(f"An exception occurred while sending AS info: {e}")
