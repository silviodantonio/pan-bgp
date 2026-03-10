import grpc

import vtysh_iface
import controller_pb2
import controller_pb2_grpc


def run():
    print("Sending neighbors ASN to controller")
    with grpc.insecure_channel("localhost:50051") as channel:
        stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

        # get info about as neighbors
        # as_neigh = vtysh_iface.get_neighbor_as()
        as_neigh = {100, 200, 300}

        response = stub.SendNeighborsASN(controller_pb2.ASList(as_list=as_neigh))

    print("Greeter client received: " + response.status)

if __name__=='__main__':
    # logging.basicConfig()
    run()
