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

        # TODO: this function contains duplicate code, can be shortened.

        local_as = topology_graph.nodes.get(request.local_as)
        dest_prefix = request.dest_prefix

        logger.info(f'AS {local_as.id} requested paths for prefix {dest_prefix}')

        # check if prefix is attached to some known AS
        dest_as_id = topology_graph.prefix_as_table.get(dest_prefix)
        if dest_as_id is None:
            # if it's not, return empty path list
            logger.info(f'No known AS owns {dest_prefix}')
            path = controller_pb2.ASPath(as_path=[])
            return controller_pb2.Paths(paths=[path])

        dest_as = topology_graph.nodes.get(dest_as_id)

        logger.debug(f"Current AS topology: \n{topology_graph}")

        #check if source_as and dest_as are in the same graph component
        logger.debug(f"Computing nodes reachable from {local_as.id}")
        source_as_component = topology_graph.reachable_nodes_from(local_as)
        if dest_as in source_as_component:
            logger.debug(f"AS {local_as.id} and AS {dest_as.id} belong to the same component")

            # If so, search for a path
            logger.debug(f"Finding paths for {dest_prefix}")
            found_paths = topology_graph.find_all_paths(local_as, dest_as)
            # Convert paths from objects to list of ids:
            found_paths_ids = []
            for path in found_paths:
                found_paths_ids.append([as_info.id for as_info in path])

            logger.debug(f"Returning paths for {dest_prefix}")
            return controller_pb2.Paths(paths=[controller_pb2.ASPath(as_path=path) for path in found_paths_ids])

        else:
            logger.debug(f"AS {local_as.id} and AS {dest_as.id} belong to different components")
            graph_components = topology_graph.get_components()

            # extract components for source and dest nodes.
            source_comp = set()
            dest_comp = set()
            for component in graph_components:
                if local_as in component:
                    source_comp = component
                    break
            for component in graph_components:
                if dest_as in component:
                    dest_comp = component
                    break

            # Build a new graph, building fictitous connections between components
            logger.debug(f"Connecting components of AS {local_as.id} and AS {dest_as.id}")
            # NOTE: I really want to avoid this copy
            working_topology_graph = copy.deepcopy(topology_graph)
            logger.debug("Successfully copied topology graph")
            working_topology_graph.connect_components(source_comp, dest_comp)

            # Since now we are working on a copy, references to local_as and dest_as
            # must be updated
            local_as = working_topology_graph.nodes.get(local_as.id)
            dest_as = working_topology_graph.nodes.get(dest_as_id)

            # compute paths as before
            logger.debug(f"Finding paths for {dest_prefix}")
            found_paths = working_topology_graph.find_all_paths(local_as, dest_as)
            logger.debug(f"Updated topology: \n{working_topology_graph}")
            logger.debug(f"Source AS {local_as.id} is connected to dest AS {dest_as.id} = {dest_as in working_topology_graph.reachable_nodes_from(local_as)}")
            # Convert paths from objects to list of ids:
            found_paths_ids = []
            for path in found_paths:
                found_paths_ids.append([as_info.id for as_info in path])

            logger.debug(f"Found paths:\n{found_paths_ids}")

            logger.debug(f"Returning paths for {dest_prefix}")
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
