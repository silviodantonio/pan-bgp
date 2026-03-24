import logging

def get_logger(name):

    logger = logging.getLogger(name)

    # Logger configuration
    # TODO: add logging setup in config file

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    file_handler = logging.FileHandler("/var/log/pangbp.log")
    file_handler.setFormatter(formatter)

    # Tell logger to output to file.
    logger.addHandler(file_handler)

    return logger
