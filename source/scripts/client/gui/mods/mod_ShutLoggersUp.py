import logging

logging.getLogger(__name__)
logging.info('Disabling loggers info')
logging.disable(logging.INFO)
logging.info('If you see this message - something went terribly wrong')
