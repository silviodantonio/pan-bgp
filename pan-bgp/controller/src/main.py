from concurrent import futures

import grpc

import graph
import config
import utils
import controller_pb2       # Contains message type definitions
import controller_pb2_grpc  # Contains stubs and other stuf for building the server

# known_as = {}

# Get a pre-configured logger instance
logger = utils.get_logger(__name__)

topology_graph = graph.NetworkGraph()

# Maybe return ids instead of AS objects?

def request_path(topology_graph: graph.NetworkGraph, 
                 source_as: graph.NetworkGraph,
                 dest_prefix: str,
                 policy: str,
                 num: int) -> list[list[graph.AS]]:

    found_paths = []

    # Check if the destination prefix is known
    dest_as_id = topology_graph.prefix_table.get(dest_prefix)
    if dest_as_id is None:
        logger.info(f'No known AS owns {dest_prefix}')
        return found_paths
    # Get dest_as object from topology graph
    dest_as = topology_graph.ases.get(dest_as_id)

    logger.debug(f"Current AS topology: {topology_graph}")

    # NOTE: other two policies to add could be:
    # controlled_paths, controlled_midpoints.

    # attempt to populate the found_paths list.
    if policy == 'trusted_paths':
        found_paths = topology_graph.trusted_paths(source_as, dest_as)
    else:
        logger.info("Unknown policy")

    # Pick the number of paths requested
    found_paths = found_paths[:num]

    return found_paths


# Implementation of the stub contained in pb2_grpc
class ControllerMessagingService(controller_pb2_grpc.ControllerMessagingServiceServicer):

    def SendASInfo(self, request, context):

        local_as_num = request.local_as
        peers_list = request.remote_as_list
        prefix_list = request.prefix_list

        logger.info(f"Received info message from AS{local_as_num}")
        logger.debug(f"ASN: {local_as_num}, neighbors: {peers_list}, prefixes: {prefix_list}")

        # if not exists, build a new node
        if local_as_num not in topology_graph.ases:
            logger.info(f"Creating object for AS{local_as_num}")
            new_as = graph.AS(local_as_num, peers_list)
            for prefix in prefix_list:
                new_as.announces_prefix(prefix)
            topology_graph.add_as(new_as)

        return controller_pb2.ResponseStatus(status="OK")

    def RequestPath(self, request, context):

        # Extract data from request message
        dest_prefix = request.destination.dest_prefix
        local_as_id = request.destination.local_as
        local_as = topology_graph.ases.get(local_as_id)
        policy = request.policy.policy
        number_paths = request.number_of_paths

        logger.info(f'AS {local_as.number} requested {number_paths} paths for prefix {dest_prefix} with policy {policy}')

        found_paths = request_path(
            topology_graph, local_as, dest_prefix, policy, number_paths)

        # Convert paths from objects to list of ids:
        found_paths_ids = []
        for path in found_paths:
            found_paths_ids.append([as_info.number for as_info in path])

        logger.debug(f"Returning paths for {dest_prefix}:\n{found_paths_ids}")

        # Return a list of ASPaths. Each ASPath is a list of ASN
        paths = [controller_pb2.ASPath(as_path=path)
                 for path in found_paths_ids]
        return controller_pb2.Paths(paths=paths)


def serve(port):
    # ensure that port is a string
    port = str(port)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    controller_pb2_grpc.add_ControllerMessagingServiceServicer_to_server(
        ControllerMessagingService(), server)
    server.add_insecure_port("[::]:" + port)
    server.start()
    logger.info(f"Server started, listening on {port}")
    server.wait_for_termination()


if __name__ == "__main__":
    config_data = config.load_config_file("/etc/panbgp/panbgp.conf")
    port = config_data['controller']['port']
    serve(port)
