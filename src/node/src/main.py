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
    # Here should go a "attempt to reconnect loop"
    controller_interface.send_as_info()
    # is this enough to induce an endless loop?
    socket_interface.start()
    sleep(5)
    controller_interface.request_path('192.0.2.0/30')
