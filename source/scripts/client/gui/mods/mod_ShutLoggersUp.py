import logging

logging.getLogger('ShutLoggersUp')
logging.info('Disabled logger level "info" and below')
logging.disable(logging.INFO)
logging.info('If you see this message - something went terribly wrong')
