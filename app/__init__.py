from flask import Flask
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions here if any

    # Register blueprints here
    from app import routes
    app.register_blueprint(routes.bp) # Assuming routes are in a blueprint named 'bp'

    return app
