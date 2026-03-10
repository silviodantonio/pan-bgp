from concurrent import futures
import logging

import grpc

import graph
import controller_pb2       # Contains message type definitions
import controller_pb2_grpc  # Contains stubs and other stuf for building the server

topology_graph = graph.DirectedGraph()
def add_neighbors(local_as, remote_as_list):
    try:
        topology_graph.add_node(local_as)
        for remote_as in remote_as_list:
            topology_graph.add_edge(local_as, remote_as)
    except ValueError:
        logging.warning("An error occured while updating the topology graph")


# Implementation of the stub contained in pb2_grpc
class ControllerMessagingService(controller_pb2_grpc.ControllerMessagingServiceServicer):

    def SendNeighborsASN(self, request, context):
        logging.info(f"AS {request.local_as} has neigbors {request.remote_as_list}")
        # add info to topology graph
        add_neighbors(request.local_as, request.remote_as_list)
        logging.debug(topology_graph)
        return controller_pb2.ResponseStatus(status="OK")


def serve():
    port = "50051"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    controller_pb2_grpc.add_ControllerMessagingServiceServicer_to_server(ControllerMessagingService(), server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    logging.info(f"Server started, listening on {port}")
    server.wait_for_termination()

if __name__ == "__main__":
    logging.basicConfig(filename="/var/log/pangbp.log", 
                        format="%(asctime)s %(levelname)s %(message)s",
                        level=logging.DEBUG)
    serve()
