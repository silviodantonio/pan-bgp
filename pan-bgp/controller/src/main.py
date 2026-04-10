import logging

import configurator as cf
import messaging

configurator = cf.Configurator()
logger = logging.getLogger(__name__)

if __name__ == "__main__":

    messaging.serve(configurator.controller['port'])
