import logging
from concurrent import futures

import grpc

import core
import as_data
import controller_pb2
import controller_pb2_grpc

logger = logging.getLogger(__name__)


class ControllerMessagingService(controller_pb2_grpc.ControllerMessagingServiceServicer):

    def SendASInfo(self, request, context):

        local_as_num: int = request.local_as
        identity_prefix: str = request.identity_prefix
        attached_prefixes: list[str] = request.prefix_list

        as_data.add_as(local_as_num, identity_prefix, attached_prefixes)

        return controller_pb2.ResponseStatus(status="OK")

    def RequestPath(self, request, context):

        # Extract data from request message
        dest_prefix = request.destination.dest_prefix
        local_as_id = request.destination.local_as
        policy = request.policy.policy
        number_paths = request.number_of_paths

        logger.info(f'AS {local_as_id} requested {number_paths} paths for prefix {dest_prefix} with policy {policy}')

        found_paths = core.compute_paths(local_as_id, dest_prefix, policy, number_paths)

        logger.debug(f"Returning to AS{local_as_id} paths for {dest_prefix}: {found_paths}")

        # Return a list of ASPaths. Each ASPath is a list of ASN
        paths = [controller_pb2.ASPath(as_path=path) for path in found_paths]
        return controller_pb2.Paths(paths=paths)

    def SendBGPPaths(self, request, context):

        local_as_id = request.local_as
        recv_bgp_paths = request.bgp_paths

        logger.debug(f"Got new as_paths from {local_as_id}")

        bgp_paths = []
        for recv_bgp_path in recv_bgp_paths:

            dest_prefix: str = recv_bgp_path.dest_prefix
            as_path: list[int] = recv_bgp_path.as_path
            as_path_metadata = recv_bgp_path.metadata

            # convert grpc metadata objects into a dict
            metadata_dict: dict[str, str] = {}
            for metadata_entry in as_path_metadata:
                key = metadata_entry.key
                value = metadata_entry.value
                metadata_dict[key] = value

            bgp_path_dict = {}
            bgp_path_dict["dest_prefix"] = dest_prefix
            bgp_path_dict["as_path"] = as_path
            bgp_path_dict["metadata"] = metadata_dict

            bgp_paths.append(bgp_path_dict)

        logger.info(f"Updating rib of AS{local_as_id}")
        as_data.add_as_paths(local_as_id, bgp_paths)

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
