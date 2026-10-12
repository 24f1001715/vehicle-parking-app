import os
from flask import Flask
from dotenv import load_dotenv
from models.models import db
from controllers.auth import auth_bp
from controllers.admin_routes import admin_bp
from controllers.user_routes import user_bp
from controllers.api_routes import api_bp
from controllers.ai_assistant import ai_assistant_bp

load_dotenv()

app = None

def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv('SECRET_KEY', 'supersecretkey')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///parking.sqlite3')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(ai_assistant_bp)

    app.app_context().push()
    return app

app = create_app()

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    app.run(host=host, port=port, debug=debug)
