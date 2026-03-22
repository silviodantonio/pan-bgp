from concurrent import futures
import logging
import copy

import grpc

import graph
import controller_pb2       # Contains message type definitions
import controller_pb2_grpc  # Contains stubs and other stuf for building the server

# known_as = {}

# Get a logger instance
logger = logging.getLogger(__name__)

# Logger configuration
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
file_handler = logging.FileHandler("/var/log/pangbp.log")
file_handler.setFormatter(formatter)

# Tell logger to output to file.
logger.addHandler(file_handler)


topology_graph = graph.ASGraph()

# Implementation of the stub contained in pb2_grpc
class ControllerMessagingService(controller_pb2_grpc.ControllerMessagingServiceServicer):

    def SendASInfo(self, request, context):

        local_as = request.local_as
        remote_as_list = request.remote_as_list
        prefix_list = request.prefix_list

        logger.info(f"Received info message from {local_as}")
        logger.debug(f"ASN: {local_as}, neighbors: {remote_as_list}, prefixes: {prefix_list}")

        # if not exists, build a new node
        if local_as not in topology_graph.nodes:
            logger.info(f"Creating new node for AS {local_as}")
            new_as = graph.ASNode()
            new_as.id = local_as
            new_as.prefixes = set(prefix_list)
            new_as.controlled = True
            new_as.trusted = True
            topology_graph.add_node(new_as)

        # add neighbors. if unknown AS, create a new node for them
        for neighbor_as in remote_as_list:
            logger.debug(f"Add {neighbor_as} as {local_as} neighbor")
            if neighbor_as not in topology_graph.nodes:
                logger.debug(f"{neighbor_as} is a new AS")
                new_as = graph.ASNode()
                new_as.id = neighbor_as
                topology_graph.add_node(new_as)
            topology_graph.add_edge(local_as, neighbor_as)

        return controller_pb2.ResponseStatus(status="OK")

    def RequestPath(self, request, context):

        # Extract data from request message
        dest_prefix = request.destination.dest_prefix
        local_as_id = request.destination.local_as
        local_as = topology_graph.nodes.get(local_as_id)
        policy = request.policy.policy
        number_paths = request.number_of_paths

        logger.info(f'AS {local_as.id} requested {number_paths} paths for prefix {dest_prefix} with policy {policy}')

        found_paths=[]

        # check if prefix is attached to some controlled AS
        # Note: the controller knows prefixes only for controlled ASes
        dest_as_id = topology_graph.prefix_as_table.get(dest_prefix)
        if dest_as_id is None:
            # if it's not, return empty path list
            logger.info(f'No known AS owns {dest_prefix}')
            return controller_pb2.Paths(paths=[controller_pb2.ASPath(as_path=[])])

        dest_as = topology_graph.nodes.get(dest_as_id)

        logger.debug(f"Current AS topology: \n{topology_graph}")

        # if it is, check if there's some "direct" known path
        logger.debug(f"Computing nodes reachable from {local_as.id}")
        source_as_component = topology_graph.reachable_nodes_from(local_as)
        if dest_as in source_as_component:
            logger.debug(f"AS {local_as.id} and AS {dest_as.id} belong to the same component")

            # If so, get all paths
            logger.debug(f"Finding paths for {dest_prefix}")
            found_paths = topology_graph.find_all_paths(local_as, dest_as)

        else:
            logger.debug(f"AS {local_as.id} and AS {dest_as.id} belong to different components")

            # Get all paths with trusted midpoints
            found_paths = topology_graph.trusted_midpoints_paths(local_as, dest_as)
            logger.debug(f"Computed all paths with trusted midpoints")

        # Pick the number of paths requested
        found_paths = found_paths[:number_paths]

        # Convert paths from objects to list of ids:
        found_paths_ids = []
        for path in found_paths:
            found_paths_ids.append([as_info.id for as_info in path])

        logger.debug(f"Returning paths for {dest_prefix}:\n{found_paths_ids}")
        # Return a list of ASPaths. Each ASPath is a list of ASN
        return controller_pb2.Paths(paths=[controller_pb2.ASPath(as_path=path) for path in found_paths_ids])

def serve():
    port = "50051"
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    controller_pb2_grpc.add_ControllerMessagingServiceServicer_to_server(ControllerMessagingService(), server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    logger.info(f"Server started, listening on {port}")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
