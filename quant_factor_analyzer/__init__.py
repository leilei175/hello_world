from flask import Flask, render_template # Added render_template
import os # Added os

def create_app():
    app = Flask(__name__, instance_relative_config=True) 
    
    # Load the configuration from config.py at the project root
    app.config.from_pyfile('../config.py', silent=False) 
    
    # Ensure instance path exists.
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)

    # Create upload directories within the instance path using paths from config
    # UPLOAD_FOLDER_DATA and UPLOAD_FOLDER_PRICES in config.py are relative to 'instance/'
    data_upload_abs_path = os.path.join(app.instance_path, app.config['UPLOAD_FOLDER_DATA'])
    prices_upload_abs_path = os.path.join(app.instance_path, app.config['UPLOAD_FOLDER_PRICES'])

    os.makedirs(data_upload_abs_path, exist_ok=True)
    os.makedirs(prices_upload_abs_path, exist_ok=True)

    with app.app_context():
        # Import parts of our application
        from .data_management import routes as data_routes
        from .visualization import routes as vis_routes # Added visualization routes
        # from .factor_analysis import analysis_routes
        
        # Register Blueprints
        app.register_blueprint(data_routes.data_bp, url_prefix='/data')
        app.register_blueprint(vis_routes.vis_bp, url_prefix='/visualization') # Registered vis_bp
        # app.register_blueprint(analysis_routes.bp)
        
        @app.route('/')
        def index():
            return render_template('index.html')
        
        @app.route('/hello')
        def hello():
            return 'Hello from create_app!'
    
    return app
