from logging.handlers import RotatingFileHandler
import logging

def start_logging(app):
    formatter = logging.Formatter('%(asctime)s: %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
    logfile = app.config['CATALOG_LOGFILE']
    handler = RotatingFileHandler(logfile, maxBytes=10000, backupCount=1) # Rotates files when they get too large
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)