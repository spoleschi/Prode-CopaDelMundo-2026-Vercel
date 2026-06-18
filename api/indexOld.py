from flask import Flask

from api.config import Config
from routes.auth_routes import auth_bp
from routes.main_routes import main_bp
from routes.admin_routes import admin_bp
from routes.prediction_routes import prediction_bp
from routes.group_routes import group_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(prediction_bp)
    app.register_blueprint(group_bp)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)