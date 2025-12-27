from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import datetime
import logging
from logging.handlers import RotatingFileHandler
import os

# Load environment variables
load_dotenv()

db = SQLAlchemy()
migrate = None


def create_app():
    app = Flask(__name__, template_folder='../templates',
                static_folder='../static')
    app.config['SECRET_KEY'] = 'supersecretkey'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configure logging
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/easypark.log', maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('EasyPark startup')

    @app.before_request
    def session_management():
        if 'user_id' in session:
            now = datetime.datetime.utcnow().timestamp()
            last_activity = session.get('last_activity', now)
            if now - last_activity > 600:  # 10 minutes
                session.pop('user_id', None)  # Logout user
            else:
                session['last_activity'] = now

    db.init_app(app)

    global migrate
    migrate = Migrate(app, db)

    from .routes import main
    app.register_blueprint(main)

    return app
