from concurrent import futures
import copy

import grpc

import graph
import config
import utils
import controller_pb2       # Contains message type definitions
import controller_pb2_grpc  # Contains stubs and other stuf for building the server

# known_as = {}

# Get a pre-configured logger instance
logger = utils.get_logger(__name__)

topology_graph = graph.ASGraph()

# Maybe return ids instead of AS objects?
def request_path(topology_graph: graph.ASGraph, source_as: graph.AS, dest_prefix: str, policy: str, num: int) -> list[list[graph.AS]]:

        found_paths = []

        # Check if the destination prefix is known
        dest_as_id = topology_graph.prefix_as_table.get(dest_prefix)
        if dest_as_id is None:
            logger.info(f'No known AS owns {dest_prefix}')
            return found_paths
        # Get dest_as object from topology graph
        dest_as = topology_graph.nodes.get(dest_as_id)

        logger.debug(f"Current AS topology: \n{topology_graph}")

        # NOTE: other two policies to add could be:
        # controlled_paths, controlled_midpoints.

        # attempt to populate the found_paths list.
        if policy == 'trusted_paths':

            source_as_component = topology_graph.reachable_nodes_from(source_as)
            if dest_as in source_as_component:
                logger.debug(f"AS {source_as.id} and AS {dest_as.id} belong to the same component")
                # Then there's some hope to find some paths.
                logger.debug(f"Finding chain of trusted ASes for {dest_prefix}")
                found_paths = topology_graph.find_trusted_paths(source_as, dest_as)

        else:
            # return empty list
            logger.info("Unknown policy")

        # Pick the number of paths requested
        found_paths = found_paths[:num]

        return found_paths


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
            new_as = graph.AS()
            new_as.id = local_as
            new_as.prefixes = set(prefix_list)
            new_as.controlled = True
            new_as.trusted = True
            topology_graph.add_node(new_as)

        # Add edges for known neighbors
        for neighbor_as in remote_as_list:
            if neighbor_as in topology_graph.nodes:
                logger.debug(f"{local_as} has known neighbor {neighbor_as}")
                logger.debug(f"Add edge {local_as}, {neighbor_as}")
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


        found_paths = request_path(topology_graph, local_as, dest_prefix, policy, number_paths)

        # Convert paths from objects to list of ids:
        found_paths_ids = []
        for path in found_paths:
            found_paths_ids.append([as_info.id for as_info in path])

        logger.debug(f"Returning paths for {dest_prefix}:\n{found_paths_ids}")
        # Return a list of ASPaths. Each ASPath is a list of ASN
        return controller_pb2.Paths(paths=[controller_pb2.ASPath(as_path=path) for path in found_paths_ids])

def serve(port):
    # ensure that port is a string
    port = str(port)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    controller_pb2_grpc.add_ControllerMessagingServiceServicer_to_server(ControllerMessagingService(), server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    logger.info(f"Server started, listening on {port}")
    server.wait_for_termination()

if __name__ == "__main__":
    config_data = config.load_config_file("/etc/panbgp/panbgp.conf")
    port = config_data['controller']['port']
    serve(port)
