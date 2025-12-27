from contextlib import contextmanager

from flask import Flask, render_template
from flask_login import LoginManager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from app.config import Config
from app.database.models import User, Course, Pricing

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
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)

    # Initialize SQLAlchemy engine
    engine = create_engine(
        Config.DATABASE_URL,
        echo=app.config.get('SQLALCHEMY_ECHO', False)
    )
    # Use scoped_session for thread-safe sessions
    SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

    @login_manager.user_loader
    def load_user(user_id):
        if user_id is None or user_id == 'None':
            return None

        try:
            session = SessionLocal()
            user = session.query(User).filter_by(id=int(user_id)).first()

            if user:
                return user

            session.close()
            return None
        except (ValueError, TypeError, Exception) as e:
            print(f"Error loading user: {e}")
            return None

    # Teardown to remove session after each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        SessionLocal.remove()

    # Register blueprints
    from app.routes.auth import auth as auth_blueprint
    from app.routes.customer import customer as customer_blueprint
    from app.routes.course import course as course_blueprint
    from app.routes.admin import admin as admin_blueprint
    from app.routes.hiragana import hiragana_bp  # Import the hiragana blueprint

    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    app.register_blueprint(customer_blueprint, url_prefix='/dashboard')
    app.register_blueprint(course_blueprint, url_prefix='/course')  # Note: changed from /dashboard to /course
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    app.register_blueprint(hiragana_bp)  # Register the hiragana blueprint

    # Index page
    @app.route('/')
    def index():
        with get_session() as db:
            # Get prices for each course
            courses = db.query(Course).all()

            prices = {}
            for course in courses:
                pricing = db.query(Pricing).filter_by(course_id=course.id).first()
                prices[course.name.lower()] = pricing.price if pricing else 'N/A'

            return render_template('index.html',
                                   hiragana_price=prices.get('hiragana', 'N/A'),
                                   katakana_price=prices.get('katakana', 'N/A'),
                                   kanji_price=prices.get('kanji', 'N/A'))

    return app