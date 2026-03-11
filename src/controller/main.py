from concurrent import futures
import logging

import grpc

import graph
import controller_pb2       # Contains message type definitions
import controller_pb2_grpc  # Contains stubs and other stuf for building the server

# known_as = {}

topology_graph = graph.Graph()

# Implementation of the stub contained in pb2_grpc
class ControllerMessagingService(controller_pb2_grpc.ControllerMessagingServiceServicer):

    def SendNeighborsASN(self, request, context):

        logging.info(f"AS {request.local_as} has neigbors {request.remote_as_list}")

        local_as = request.local_as
        remote_as_list = request.remote_as_list

        # if not exists, build a new node
        if local_as not in topology_graph.nodes:
            logging.debug(f"Creating new node for AS {local_as}")
            new_as = graph.ASNode()
            new_as.id = local_as
            topology_graph.add_node(new_as)

        # mark it as controlled
        topology_graph.nodes.get(local_as).controlled = True
        logging.debug(f"Marked AS {local_as} as controlled")

        # add neighbors
        for neighbor_as in remote_as_list:
            logging.debug(f"Add {neighbor_as} as {local_as} neighbor")
            if neighbor_as not in topology_graph.nodes:
                logging.debug(f"{neighbor_as} is a new AS")
                new_as = graph.ASNode()
                new_as.id = neighbor_as
                topology_graph.add_node(new_as)
            topology_graph.add_edge(local_as, neighbor_as)

        return controller_pb2.ResponseStatus(status="OK")

    def SendPrefixes(self, request, context):
        logging.info(f"AS {request.local_as} has prefixes {request.prefix_list}")

        local_as = topology_graph.nodes.get(request.local_as)
        prefix_list = request.prefix_list

        for prefix in prefix_list:
            local_as.prefixes.add(prefix)

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
