import logging

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

# start message exchange with controller
def send_as_info():

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

def request_path(dest_prefix):

    with grpc.insecure_channel(controller_addr_str) as channel:
        stub = controller_pb2_grpc.ControllerMessagingServiceStub(channel)

        local_as = border_router.local_as
        logger.info(f"Requesting paths for {dest_prefix}")

        request = controller_pb2.Destination(local_as=local_as, dest_prefix=dest_prefix)
        response = stub.RequestPath(request)

        # Do i really need to do this or is translation automatic?
        paths = []
        for path in response.paths:
            # path is an ASPath object
            # paths.append(list(path)) # This is not working
            paths.append(path.as_path)

        logger.info(f"Received paths {paths}")
        return paths
