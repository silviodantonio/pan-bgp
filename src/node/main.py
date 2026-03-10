import os
import sys

import grpc

import vtysh_iface
import controller_pb2
import controller_pb2_grpc

controller_addr = os.environ.get('CONTROLLER_ADDR_IPv4')
controller_port = os.environ.get('CONTROLLER_PORT')

if controller_addr is None or controller_port is None:
    raise ValueError('Required environment variables not set')
    sys.exit(1)

controller_addr_str = f'{controller_addr}:{controller_port}'


def run():
    print("Sending neighbors ASN to controller")
    with grpc.insecure_channel(controller_addr_str) as channel:
        stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

        # get info about as neighbors
        # as_neigh = vtysh_iface.get_neighbor_as()
        as_neigh = {100, 200, 300}

        response = stub.SendNeighborsASN(controller_pb2.ASList(as_list=as_neigh))

    print("Greeter client received: " + response.status)

if __name__=='__main__':
    # logging.basicConfig()
    run()
    sys.exit(0)
