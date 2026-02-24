# Japanese Learning Hub

A Flask-based web application for learning Japanese characters (Hiragana, Katakana and Kanji) using a local CNN model with user authentication,
course enrollment, and progress tracking.

## Features

- User authentication with role-based access (Admin and Customer)
- Course management for Japanese character learning
- Progress tracking for individual characters
- Transaction and enrollment system
- Audio support for character pronunciation

## Tech Stack

- **Backend**: Flask + SQLAlchemy
- **Authentication**: Flask-Login
- **Database**: SQLite (configurable to PostgreSQL/MySQL)
- **Password Hashing**: Werkzeug

## Project Structure

```
.
├── app/
│   ├── web/
│   │   ├── static/      # CSS, JS, images, audio files
│   │   └── templates/   # HTML templates
│   ├── routes/          # Flask blueprints
│   ├── models.py        # Database models
│   └── config.py        # Configuration
├── run.py               # Application entry point
├── requirements.txt     # Python dependencies
└── .env                 # Environment variables
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   Copy `.env.example` to `.env` or create a `.env` file in the project root with the following:
   ```
    SECRET_KEY=your-secret-key-here
    DATABASE_URL=sqlite:///database.sqlite
    HOST=0.0.0.0
    PORT=5000
    DEBUG=True
   ```

## Database Setup

### Create the database

```bash
python run.py --create
```

### Seed the database with sample data

```bash
python run.py --seed
```

### Create and seed in one command

```bash
python run.py --create ; python run.py --seed
```

**Default seeded users:**

- **Admin**: username: `admin`, password: `password123`
- **Student 1**: username: `johndoe`, password: `password`

## Running the Application

### Development mode

```bash
python run.py
```

The application will be available at `http://localhost:5000`

### Production mode

Set `DEBUG=False` in your `.env` file and use a production WSGI server:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
```

## Database Models

- **Role**: User roles (Admin, Customer)
- **User**: User accounts with authentication
- **Course**: Japanese learning courses
- **Character**: Individual characters (Hiragana/Katakana/Kanji)
- **Pricing**: Course pricing information
- **Transaction**: Purchase transactions
- **Enrollment**: User course enrollments
- **Progress**: User learning progress per character

## Development

### Web Assets

- Static files (CSS, JS, images): `app/web/static/`
- HTML templates: `app/web/templates/`

### Adding Routes

Create blueprints in `app/routes/` and register them in `app/__init__.py`

### Database Migrations

Modify models in `models.py`, then clear and reseed:

```bash
python run.py --clear
python run.py --seed
```

## Configuration

Edit `app/config.py` or set environment variables:

- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: Flask secret key for sessions
- `DEBUG`: Debug mode (True/False)
