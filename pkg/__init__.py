from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from pkg.config import LiveConfig

# Initialize extensions GLOBALLY - outside create_app
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()  # <- THIS MUST BE GLOBAL

def ensure_user_table_schema():
    from pkg.models import db
    inspector = db.inspect(db.engine)
    
    if 'users' not in inspector.get_table_names():
        return
        
    columns = {col['name'] for col in inspector.get_columns('users')}
    
    if 'user_id' not in columns and 'id' not in columns:
        db.session.execute(text('ALTER TABLE users ADD COLUMN user_id INT AUTO_INCREMENT PRIMARY KEY'))
    
    needed_columns = {
        'username': 'VARCHAR(45) NOT NULL',
        'email': 'VARCHAR(100) NOT NULL',
        'password': 'VARCHAR(255) NOT NULL',
        'phone_number': 'VARCHAR(20)',
        'state_id': 'INT',
        'created_at': 'DATETIME'
    }
    
    for column_name, definition in needed_columns.items():
        if column_name not in columns:
            try:
                db.session.execute(text(f'ALTER TABLE users ADD COLUMN {column_name} {definition}'))
            except Exception:
                db.session.rollback()
                break
    db.session.commit()

def create_app():
    from pkg.models import User
    from pkg.user_routes import user_bp
    from .admin_routes import admin_bp
    
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_pyfile('config.py', silent=True)
    app.config.from_object(LiveConfig)
    

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Configure login_manager
    login_manager.login_view = 'main.login'  # blueprint.function
    login_manager.login_message = "Please login to access this page"
    login_manager.login_message_category = "info"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    with app.app_context():
        try:
            #db.create_all()
            ensure_user_table_schema()
        except SQLAlchemyError as exc:
            app.logger.error('Database initialization failed: %s', exc)
            raise
            
    return app

app = create_app()

from pkg import forms