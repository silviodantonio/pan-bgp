import sys
import logging
import tomllib

import grpc

import vtysh_iface
import controller_pb2
import controller_pb2_grpc
import socket_interface
import controller as ctrl

if __name__=='__main__':


    config_file = "/etc/panbgp/panbgp.conf"
    config_data = None

    # =============================================================================
    #   Setup loggers
    # =============================================================================

    # try to config default logger using config file
    try:

        with open(config_file, "rb") as f:
            config_data = tomllib.load(f)

        # translate logging level string into logging levels constants
        logging_config = config_data['logging']
        if logging_config['level'] == 'debug':
            logging_level = logging.DEBUG
        elif logging_config['level'] == 'info':
            logging_level = logging.INFO
        elif logging_config['level'] == 'warning':
            logging_level = logging.WARNING
        else:
            # default to error and higher severity
            logging_level = logging.ERROR

        # logging.basicConfig(filename=logging_config.file, level=logging_config.level, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
        log_file = logging_config.get('file')
        if log_file is None:
            log_file = "/var/log/panbgp.log"
        logging.basicConfig(filename=log_file,
                            level=logging_level,
                            format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

        logger = logging.getLogger(__name__)
        logger.info(f"Configured loggers using config file {config_file}")

    # If something goes wrong set up some defaults
    except Exception as e:
        # these logs are getting lost in the depths of the file system

        logging.basicConfig(level=logging.WARNING,
                format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

        logger = logging.getLogger(__name__)
        logger.warning("Something went wrong while configuring loggers, using defaults settings")
        logger.warning(f"Raised exception: {e}")


    # =============================================================================
    #   Setup controller connnection
    # =============================================================================

    # try to get controller info from config data
    try:
        controller_info = config_data['controller']
        controller_addr = controller_info['address']
        controller_port = controller_info['port']

    except:
        logger.critical("Missing info about controller in config file: address and port")
        sys.exit(1)

    controller = ctrl.Controller(controller_addr, controller_port)

    controller.send_as_info()

    # =============================================================================
    #   Interactive interface setup
    # =============================================================================

    socket_interface_config = config_data.get('interactive_interface')
    if socket_interface_config is not None:
        socket_interface_addr = socket_interface_config.get('address')
        if socket_interface_addr is None:
            socket_interface_addr = '127.0.0.1'
        socket_interface_port = socket_interface_config.get('port')
        if socket_interface_port is None:
            socket_interface_port = 9999

    socket_interface.start(socket_interface_addr, socket_interface_port, controller)

    try:
        controller.request_path('192.0.2.0/30', 'none', 5)
    except Exception as e: 
        logger.debug(f"An exception occurred while sending AS info: {e}")
