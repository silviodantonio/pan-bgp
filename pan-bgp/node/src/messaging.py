import logging
import random
from time import sleep
from threading import Thread

import grpc

import core
import controller_pb2
import controller_pb2_grpc

logger = logging.getLogger(__name__)
node = core.node_singleton

# This is a decorator
def _retry_with_rand_backoff(function):
    def wrapper(*args, **kwargs):

        base = 2            # binary exponential backoff

        min_wait_time = 1
        max_wait_time = 4   # this limits max wait time

        attempt = 0
        max_attempts = 5

        wait_time = min_wait_time

        while True:
        # Try to call the function until returns something instead of
        # raising some exception

            try:
                result = function(*args, **kwargs)
                return result

            except Exception as e:
            # if something goes wrong, retry after some time
                logger.debug(f"Controller raised an exception: {e}")
                if attempt < max_attempts:
                    t = random.random() * min(wait_time, max_wait_time)
                    logger.debug(f"Attempt number {attempt+1}, retrying after {t}")
                    sleep(t)
                    wait_time *= base
                    attempt += 1
                else:
                    logger.debug("Max number of attempts exceeded")
                    # max_attempts exceeded, forwarding the exception
                    raise e
    return wrapper


class Messager:

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.address_string = f"{self.address}:{self.port}"

    @_retry_with_rand_backoff
    def send_as_info(self):

        with grpc.insecure_channel(self.address_string) as channel:
            stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

            local_as = node.local_asn
            remote_as_set = node.bgp_peers
            attached_prefixes = node.attached_prefixes

            logger.info("Sending AS info message to controller")
            logger.debug(f"Neighbors: {remote_as_set}, attached prefixes: {attached_prefixes}")

            response = stub.SendASInfo(controller_pb2.ASInfo(local_as=local_as,
                                                             remote_as_list=remote_as_set,
                                                             prefix_list=attached_prefixes))

        logger.info("Received: " + response.status)


    @_retry_with_rand_backoff
    def request_path(self, dest_prefix: str, policy: str, k: int):

        with grpc.insecure_channel(self.address_string) as channel:
            stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

            local_as = node.local_asn
            logger.info(f"Requesting paths for {dest_prefix}")

            destination_prefix = controller_pb2.Destination(local_as=local_as, dest_prefix=dest_prefix)
            policy = controller_pb2.Policy(policy=policy)
            request = controller_pb2.RequestPathMessage(destination=destination_prefix,
                                                        policy=policy, number_of_paths=k)
            response = stub.RequestPath(request)

            paths = []
            for path in response.paths:
                # path is a ASPath object
                paths.append(path.as_path)

            logger.info(f"Received paths {paths}")
            return paths


    @_retry_with_rand_backoff
    def send_as_paths(self):

        with grpc.insecure_channel(self.address_string) as channel:
            stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

            local_as = node.local_asn
            bgp_paths = node.get_paths()


            grpc_bgp_paths = []
            for dest, paths in bgp_paths.items():
                for path in paths:
                    grpc_bgp_paths.append(controller_pb2.BGPPath(destination=path.dest_as, 
                                                                 as_path=path.path))

            logger.info("Sending AS Paths to controller")
            logger.debug(f"AS Paths: {bgp_paths}")
            request = controller_pb2.BGPPaths(local_as=local_as, bgp_paths=grpc_bgp_paths)

            response = stub.SendBGPPaths(request)

            logger.info("Received: " + response.status)


class ASPathBeaconingThread(Thread):

    def __init__(self, messager: Messager, beaconing_rate: int):
        super().__init__()
        self.messager = messager
        self.beaconing_rate = beaconing_rate

    def run(self):

        while True:

            try:
                self.messager.send_as_paths()
            except Exception as e:
                logger.warn(f"Couldn't send AS Paths to controller. Raised exception:\n{e}")

            sleep(self.beaconing_rate)

