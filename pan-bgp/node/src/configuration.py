import tomllib
import logging

class Configuration:


    def __init__(self, config_file=None):

        # If nothing special is provided, use default
        if config_file == None:
            config_file = "/etc/panbgp/panbgp.conf"

        self.config_data = None
        try:
            with open(config_file, "rb") as f:
                self.config_data = tomllib.load(f)
        except Exception as e :
            # Catches error if file doesnt' exist or tomllib
            # has some troubles parsing the file contents
            raise e

        if self.config_data is None:
            raise ValueError("The configuration file cannot be empty")

        # Raise error if controller config is missing
        self.controller = self.config_data.get('controller')
        if self.controller == None:
            raise ValueError("Controller section is required in config file")

        # For these check the config file, otherwise load some defaults
        self._configure_logging()
        self._configure_interactive_interface()

        logger = logging.getLogger(__name__)
        logger.info("Configuration done")


    def _configure_logging(self) -> None:

        # defaults
        log_level = logging.WARNING
        log_file = "/var/log/panbgp.log"

        log_format = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

        self.logging = self.config_data.get('logging')

        if self.logging is not None:

            # Attempt to get configured log level
            configured_log_level = self.logging.get('level')
            if configured_log_level is not None:
                if configured_log_level == 'debug':
                    log_level = logging.DEBUG
                elif configured_log_level == 'info':
                    log_level = logging.INFO
                elif configured_log_level == 'warning':
                    log_level = logging.WARNING
                elif configured_log_level == 'error':
                    log_level = logging.ERROR
                elif configured_log_level == 'critical':
                    log_level = logging.CRITICAL

            configured_log_file = self.logging.get('file')
            if configured_log_file is not None:
                log_file = configured_log_file

        logging.basicConfig(filename=log_file, level=log_level, format=log_format)


    def _configure_interactive_interface(self) -> None:

        default_local_socket_addr = "127.0.0.1"
        default_local_socket_port = 9999

        self.interactive_interface = self.config_data.get("interactive_interface")
        # Replace defaults
        if self.interactive_interface is not None:
            if self.interactive_interface.get("address") is None:
                self.interactive_interface["address"] = default_local_socket_addr
            if self.interactive_interface.get("port") is None:
                self.interactive_interface["port"] = default_local_socket_port

