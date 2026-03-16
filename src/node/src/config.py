import tomllib
import logging

logger = logging.getLogger(__name__)

# Logger configuration
logger.setLevel(logging.DEBUG)
# Set up handler
file_handler = logging.FileHandler("/var/log/pangbp.log")
formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
file_handler.setFormatter(formatter)
# Tell logger to use file_handler
logger.addHandler(file_handler)

def load_config_file(filepath):

    config_data = None

    logger.debug(f"loaded config file: \n{filepath}")
    with open(filepath, "rb") as f:
        config_data = tomllib.load(f)
        logger.debug(f"loaded config file: \n{config_data}")

    if config_data is None:
        logger.critical("Missing required config file")
        raise FileNotFoundError("Missing required config file")

    _check_required_fields(config_data)

    return config_data

def _check_required_fields(config_data):
    # check if required fields are set
    controller_config_section = config_data.get('controller')
    if controller_config_section is None:
        logger.critical("Missing required config file")
        raise ValueError('In config file, required controller section is missing')

    controller_address = controller_config_section.get('address')
    if controller_address is None:
        logger.critical("Missing required config file")
        raise ValueError('In config file, required controller address is missing')

    controller_port = controller_config_section.get('port')
    if controller_port is None:
        logger.critical("Missing required config file")
        raise ValueError('In config file, required controller port is missing')
