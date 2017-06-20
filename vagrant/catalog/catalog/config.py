"""Sample configuration file. Needs to be overridden by a configuration file
in ../instance/config.py"""

SECRET_KEY = 'development key'
CSRF_SECRET_KEY = b'development csrf key'

# Non-standard, specific to this app
CATALOG_LOGFILE = 'catalog.log'

# Default sqlite database

DB_FILE = 'catalog.db'

DB_URL = ''