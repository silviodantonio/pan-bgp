# TODO: This module is in dire need of a cleanup
import logging
import random
from time import sleep
from threading import Thread
import hashlib

import grpc

import frr
import controller_pb2
import controller_pb2_grpc

# Get logger (hopefully configured by main thread)
logger = logging.getLogger(__name__)

border_router = frr.BorderRouter()

# This is a decorator
def _retry_with_rand_backoff(function):
    def wrapper(*args, **kwargs):
        logger.debug(f"Trying to call {function}")

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

class Controller:

    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.address_string = f"{self.address}:{self.port}"

    @_retry_with_rand_backoff
    def send_as_info(self):

        logger.info("Sending neighbors ASN to controller")
        with grpc.insecure_channel(self.address_string) as channel:
            stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

            local_as = border_router.local_as
            remote_as_set = border_router.remote_as_set
            attached_prefixes = border_router.attached_prefixes
            logger.info("Sending AS info message")
            logger.info(f"Neighbors: {remote_as_set}, attached prefixes: {attached_prefixes}")

            response = stub.SendASInfo(controller_pb2.ASInfo(local_as=local_as,
                                                             remote_as_list=remote_as_set,
                                                             prefix_list=attached_prefixes))

        logger.info("Received: " + response.status)

    @_retry_with_rand_backoff
    def request_path(self, dest_prefix: str, policy: str, k: int):

        with grpc.insecure_channel(self.address_string) as channel:
            stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

            local_as = border_router.local_as
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
    def send_as_paths(self, bgp_paths):

        with grpc.insecure_channel(self.address_string) as channel:
            stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

            local_as = border_router.local_as

            logger.debug("Building gRPC message")
            grpc_bgp_paths = []
            for dest, path in bgp_paths.items():
                grpc_bgp_paths.append(controller_pb2.BGPPath(destination=dest, as_path=path))

            request = controller_pb2.BGPPaths(local_as=local_as, bgp_paths=grpc_bgp_paths)

            logger.info("Sending BGP Paths to controller")
            response = stub.SendBGPPaths(request)

            logger.info("Received: " + response.status)

class ASPathBeaconingThread(Thread):

    def __init__(self, controller: Controller, beaconing_rate: int):
        super().__init__()
        self.beaconing_rate = beaconing_rate
        self.controller = controller

    def run(self):

        rib_hash = ""

        try:
            while True:

                logger.debug("Checking for RIB changes")

                bgp_paths = border_router.get_bgp_paths()
                new_rib_hash = hashlib.sha1(bytes(str(bgp_paths), 'utf8')).hexdigest()
                if new_rib_hash != rib_hash:
                    new_rib_hash_str = f"{new_rib_hash[:3]}...{new_rib_hash[-3:]}"
                    rib_hash_str = f"{rib_hash[:3]}...{rib_hash[-3:]}"
                    logger.info(f"Detected updated RIB. New: {new_rib_hash_str} Old: {rib_hash_str}")
                    logger.debug(f"Paths extracted: {bgp_paths}")
                    rib_hash = new_rib_hash
                    self.controller.send_as_paths(bgp_paths)
                sleep(self.beaconing_rate)
        except Exception as e:
            logger.warning(f"In beaconing thread an exception occurred: {e}")

