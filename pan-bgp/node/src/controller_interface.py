# TODO: This module is in dire need of a cleanup

import logging
import random
from time import sleep

import grpc

import vtysh_iface
import controller_pb2
import controller_pb2_grpc
import config

# Get logger and configure it
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
file_handler = logging.FileHandler("/var/log/pangbp.log")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

border_router = vtysh_iface.BorderRouter()

logger.info("Loading configuration file")
config_data = config.load_config_file('/etc/panbgp/node.conf')

controller_addr = config_data['controller']['address']
controller_port = config_data['controller']['port']
controller_addr_str = f"{controller_addr}:{controller_port}"

# This is a decorator
def retry_with_rand_backoff(function):
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

    @retry_with_rand_backoff
    def send_as_info(self):

        logger.info("Sending neighbors ASN to controller")
        with grpc.insecure_channel(controller_addr_str) as channel:
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

    @retry_with_rand_backoff
    def request_path(self, dest_prefix: str, policy: str, k: int):
        # WARN: at the moment controller ignores completely the policy.

        with grpc.insecure_channel(controller_addr_str) as channel:
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
