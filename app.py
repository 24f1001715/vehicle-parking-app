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
    
    # Database connection (supports Neon / Supabase Postgres or fallback SQLite)
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        # SQLAlchemy 1.4+ requires 'postgresql://' instead of legacy 'postgres://'
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
    else:
        db_url = 'sqlite:////tmp/parking.sqlite3' if os.environ.get('VERCEL') else 'sqlite:///parking.sqlite3'

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(ai_assistant_bp)

    with app.app_context():
        # Ensure database tables exist on serverless cold start
        try:
            db.create_all()
            from models.models import Admin
            from werkzeug.security import generate_password_hash
            if not Admin.query.first():
                admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
                admin_password = os.getenv('ADMIN_PASSWORD', 'Admin@12345')
                admin_fullname = os.getenv('ADMIN_FULLNAME', 'Super Admin')
                admin = Admin(
                    email_id=admin_email,
                    fullname=admin_fullname,
                    password=generate_password_hash(admin_password),
                    address="Admin HQ",
                    pincode="600000"
                )
                db.session.add(admin)
                db.session.commit()
        except Exception as e:
            print(f"Serverless DB init notice: {e}")

    return app

app = create_app()

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')
    app.run(host=host, port=port, debug=debug)
