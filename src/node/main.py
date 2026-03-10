import os
import sys
import logging

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
def run():
    logging.info("Sending neighbors ASN to controller")
    with grpc.insecure_channel(controller_addr_str) as channel:
        stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

        local_as = border_router.local_as
        remote_as_set = border_router.remote_as_set
        logging.info(f"Sending local AS: {local_as}, Neighbors: {remote_as_set}")

        response = stub.SendNeighborsASN(controller_pb2.ASList(local_as=local_as,
                                                               remote_as_list=remote_as_set))

    logging.info("Received: " + response.status)

if __name__=='__main__':
    logging.basicConfig(filename='/var/log/panbgp.log',
                        level=logging.DEBUG)
    run()
    sys.exit(0)
