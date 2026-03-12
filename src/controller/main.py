from concurrent import futures
import logging

import grpc

import graph
import controller_pb2       # Contains message type definitions
import controller_pb2_grpc  # Contains stubs and other stuf for building the server

# known_as = {}

topology_graph = graph.ASGraph()

# Implementation of the stub contained in pb2_grpc
class ControllerMessagingService(controller_pb2_grpc.ControllerMessagingServiceServicer):

    def SendASInfo(self, request, context):

        local_as = request.local_as
        remote_as_list = request.remote_as_list
        prefix_list = request.prefix_list

        logging.info(f"Received info message from {local_as}")
        logging.debug(f"ASN: {local_as}, neighbors: {remote_as_list}, prefixes: {prefix_list}")

        # if not exists, build a new node
        if local_as not in topology_graph.nodes:
            logging.info(f"Creating new node for AS {local_as}")
            new_as = graph.ASNode()
            new_as.id = local_as
            new_as.prefixes = set(prefix_list)
            new_as.controlled = True
            topology_graph.add_node(new_as)

        # add neighbors. if unknown AS, create a new node for them
        for neighbor_as in remote_as_list:
            logging.debug(f"Add {neighbor_as} as {local_as} neighbor")
            if neighbor_as not in topology_graph.nodes:
                logging.debug(f"{neighbor_as} is a new AS")
                new_as = graph.ASNode()
                new_as.id = neighbor_as
                topology_graph.add_node(new_as)
            topology_graph.add_edge(local_as, neighbor_as)

        return controller_pb2.ResponseStatus(status="OK")

    def RequestPath(self, request, context):

        local_as = topology_graph.nodes.get(request.local_as)
        dest_prefix = request.dest_prefix

        logging.info(f'AS {local_as.id} requested paths for prefix {dest_prefix}')

        # check if prefix is attached to some known AS
        dest_as_id = topology_graph.prefix_as_table.get(dest_prefix)
        if dest_as_id is None:
            logging.info(f'No known AS owns {dest_prefix}')
            return controller_pb2.ASPath(as_path=[])
        dest_as = topology_graph.nodes.get(dest_as_id)

        # get all paths
        paths = topology_graph.find_all_paths(local_as, dest_as)
        first_path = [as_info.id for as_info in paths[0]]

        # TODO: get gRPC to return multiple paths
        return controller_pb2.ASPath(as_path=first_path)

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
