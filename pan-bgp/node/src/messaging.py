import logging
import random
from time import sleep
from threading import Thread

import grpc

from frr import Path
import controller_pb2
import controller_pb2_grpc

logger = logging.getLogger(__name__)

# This is a decorator
def _retry_with_rand_backoff(function):
    def wrapper(*args, **kwargs):

        base = 2            # binary exponential backoff

        min_wait_time = 1
        max_wait_time = 4   # [seconds] this limits max wait time

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
                logger.debug(f"Controller raised an exception while calling {function}: {e}")
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

    def __init__(self, config_data: dict[str], node):

        self.address = config_data["controller_address"]
        self.port = config_data["controller_port"]
        self.address_string = f"{self.address}:{self.port}"
        self.beaconing_rate = config_data["beaconing_rate"]
        self.node = node

    @_retry_with_rand_backoff
    def send_as_info(self):

        with grpc.insecure_channel(self.address_string) as channel:
            stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

            local_as = self.node.asn
            identity_prefix = self.node.identity_prefix
            attached_prefixes = self.node.attached_prefixes

            logger.info("Sending AS info message to controller")
            logger.debug(f"Info: AS{local_as} ({identity_prefix}), attached prefixes: {attached_prefixes}")

            response = stub.SendASInfo(controller_pb2.ASInfo(local_as=local_as,
                                                             identity_prefix=identity_prefix,
                                                             prefix_list=attached_prefixes))

        logger.info("Received: " + response.status)


    @_retry_with_rand_backoff
    def request_path(self, dest_prefix: str, policy: str, k: int):

        with grpc.insecure_channel(self.address_string) as channel:
            stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

            local_as = self.node.asn
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

            local_as = self.node.asn
            as_paths: dict[str, Path] = self.node.get_as_paths()

            # construct grpc BGPPath objects
            grpc_bgp_paths: list[controller_pb2.BGPPath] = []
            for dest_prefix, as_path in as_paths.items():
                # extract metadata from Path object
                path_metadata = []
                for key, value in as_path.metadata.items():
                    grpc_metadata_entry = controller_pb2.Metadata(key=str(key), value=str(value))
                    path_metadata.append(grpc_metadata_entry)

                grpc_bgp_path = controller_pb2.BGPPath(dest_prefix=as_path.dest_prefix, 
                                               as_path=as_path.path,
                                               metadata=path_metadata)
                grpc_bgp_paths.append(grpc_bgp_path)


            logger.info("Sending AS Paths to controller")
            request = controller_pb2.BGPPaths(local_as=local_as, bgp_paths=grpc_bgp_paths)

            response = stub.SendBGPPaths(request)

            logger.info("Received: " + response.status)

    def start_path_beaconing(self, beaconing_rate):

        beaconing_thread = _BeaconingThread(self, beaconing_rate)
        beaconing_thread.start()

class _BeaconingThread(Thread):

    def __init__(self, messager: Messager, beaconing_rate: int):
        super().__init__()
        self.messager = messager
        self.beaconing_rate = beaconing_rate

    def run(self):

        while True:

            try:
                self.messager.send_as_paths()
            except Exception as e:
                logger.warning(f"Couldn't send AS Paths to controller. Raised exception:\n{e}")

            sleep(self.beaconing_rate)
