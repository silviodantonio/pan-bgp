import os
import sys
import logging
from time import sleep # temporary import until concurrency issues are fixed

import grpc

import vtysh_iface
import controller_pb2
import controller_pb2_grpc

# get info about address and port of the controller
controller_addr = os.environ.get('CONTROLLER_ADDR_IPv4')
controller_port = os.environ.get('CONTROLLER_PORT')

if controller_addr is None or controller_port is None:
    raise ValueError('Required environment variables not set')
    sys.exit(1)
controller_addr_str = f'{controller_addr}:{controller_port}'

border_router = vtysh_iface.BorderRouter()

# start message exchange with controller
def send_as_info():

    logging.info("Sending neighbors ASN to controller")
    with grpc.insecure_channel(controller_addr_str) as channel:
        stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

        local_as = border_router.local_as
        remote_as_set = border_router.remote_as_set
        attached_prefixes = border_router.attached_prefixes
        logging.info("Sending AS info message")
        logging.info(f"Neighbors: {remote_as_set}, attached prefixes: {attached_prefixes}")

        response = stub.SendASInfo(controller_pb2.ASInfo(local_as=local_as,
                                                         remote_as_list=remote_as_set,
                                                         prefix_list=attached_prefixes))

    logging.info("Received: " + response.status)

def request_path(dest_prefix):

    with grpc.insecure_channel(controller_addr_str) as channel:
        stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

        local_as = border_router.local_as
        logging.info(f"Requesting paths for {dest_prefix}")

        request = controller_pb2.Destination(local_as=local_as, dest_prefix=dest_prefix)
        response = stub.RequestPath(request)

        # Do i really need to do this or is translation automatic?
        paths = []
        for path in response.paths:
            # path is an ASPath object
            # paths.append(list(path)) # This is not working
            paths.append(path.as_path)

        logging.info(f"Received paths {paths}")
        return paths


if __name__=='__main__':
    logging.basicConfig(filename='/var/log/panbgp.log',
                        level=logging.DEBUG)
    send_as_info()
    sleep(5)
    request_path('192.0.2.0/30')

    sys.exit(0)
