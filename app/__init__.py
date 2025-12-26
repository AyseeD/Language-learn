from contextlib import contextmanager

from flask import Flask, render_template
from flask_login import LoginManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask_cors import CORS

from app.config import Config
from app.database.models import User

# Global engine and session
engine = None
SessionLocal = None
login_manager = None


def get_engine():
    return engine


@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def create_app():
    global engine, SessionLocal, login_manager

    app = Flask(__name__, static_url_path='', static_folder='web/static', template_folder='web/templates')

    # Load configuration
    app.config.from_object(Config)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    # Initialize SQLAlchemy engine
    engine = create_engine(
        Config.DATABASE_URL,
        echo=app.config.get('SQLALCHEMY_ECHO', False)
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    @login_manager.user_loader
    def load_user(user_id):
        session = SessionLocal()
        try:
            return session.query(User).get(int(user_id))
        finally:
            session.close()

    # Register blueprints
    from app.routes.auth import auth as auth_blueprint
    from app.routes.customer import customer as customer_blueprint
    from app.routes.course import course as course_blueprint

    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(customer_blueprint, url_prefix='/dashboard')
    app.register_blueprint(course_blueprint, url_prefix='/dashboard')

    # Index page
    @app.route('/')
    def index():
        return render_template('index.html')

    CORS(app)

    return app
