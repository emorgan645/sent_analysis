import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask
from flask.logging import create_logger
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy

from config import Config

app = Flask(__name__)
log = create_logger(app)
app.static_folder = 'static'
app.config.from_object(Config)

bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
mail = Mail(app)
migrate = Migrate(app, db)
moment = Moment(app)

login = LoginManager(app)
login.login_view = 'login'

# will log all errors to log file when not in debug mode
if not app.debug:

    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240, backupCount=10)
    # setFormatter provides custom formatting for the log messages
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    log.addHandler(file_handler)
    # allows handler to get the INFO level message
    log.setLevel(logging.INFO)
    log.info('Sentiment startup')

from app import routes, models, errors
