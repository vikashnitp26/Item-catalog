from flask import Flask
app = Flask(__name__, instance_relative_config=True)

app.config.from_object('catalog.config')
app.config.from_pyfile('config.py')

from . import views

# Allow logging
from .logging_config import start_logging
start_logging(app)