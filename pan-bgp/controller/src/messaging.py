import logging
from concurrent import futures

import grpc

import core
import controller_pb2
import controller_pb2_grpc

logger = logging.getLogger(__name__)


class ControllerMessagingService(controller_pb2_grpc.ControllerMessagingServiceServicer):

    def SendASInfo(self, request, context):

        local_as_num = request.local_as
        peers_list = request.remote_as_list
        prefix_list = request.prefix_list

        logger.info(f"Received info message from AS{local_as_num}")
        logger.debug(f"ASN: {local_as_num}, neighbors: {peers_list}, prefixes: {prefix_list}")

        core.add_as(local_as_num, peers_list, prefix_list)

        return controller_pb2.ResponseStatus(status="OK")

    def RequestPath(self, request, context):

        # Extract data from request message
        dest_prefix = request.destination.dest_prefix
        local_as_id = request.destination.local_as
        policy = request.policy.policy
        number_paths = request.number_of_paths

        logger.info(f'AS {local_as_id} requested {number_paths} paths for prefix {dest_prefix} with policy {policy}')

        found_paths = core.compute_paths(local_as_id, dest_prefix, policy, number_paths)

        logger.debug(f"Returning paths for {dest_prefix}:\n{found_paths}")

        # Return a list of ASPaths. Each ASPath is a list of ASN
        paths = [controller_pb2.ASPath(as_path=path) for path in found_paths]
        return controller_pb2.Paths(paths=paths)

    def SendBGPPaths(self, request, context):


        local_as_id = request.local_as
        recv_bgp_paths = request.bgp_paths

        logger.debug(f"Got new as_paths from {local_as_id}")

        # convert gRPC object to dict
        bgp_paths = {}
        for recv_bgp_path in recv_bgp_paths:
            bgp_paths[recv_bgp_path.destination] = recv_bgp_path.as_path

        core.add_bgp_paths(local_as_id, bgp_paths)

        return controller_pb2.ResponseStatus(status="OK")


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
