from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash

from app.config import Config
from app.database.models import Base, Role, User, Course, Character, Pricing, Transaction, Enrollment

# Database configuration
engine = create_engine(Config.DATABASE_URL, echo=True)
Session = sessionmaker(bind=engine)


def clear_database():
    print("[INFO] Clearing database...")
    Base.metadata.drop_all(engine)
    print("[INFO] Database cleared successfully\n")


def seed_database():
    # Create tables
    Base.metadata.create_all(engine)

    session = Session()

    try:
        # Seed Roles
        roles_data = [
            {'code': 'admin', 'name': 'Admin'},
            {'code': 'customer', 'name': 'Customer'},
        ]

        roles = []
        for role_data in roles_data:
            role = Role(**role_data)
            session.add(role)
            roles.append(role)

        session.commit()
        print("[INFO]: Roles seeded successfully")

        # Seed Users
        users_data = [
            {
                'name': 'Admin',
                'username': 'admin',
                'password': 'password',
                'role_code': 'admin'
            },
            {
                'name': 'John Doe',
                'username': 'johndoe',
                'password': 'password',
                'role_code': 'customer'
            },
            {
                'name': 'Jane Smith',
                'username': 'janesmith',
                'password': 'password_1234',
                'role_code': 'customer'
            }
        ]

        users = []
        for user_data in users_data:
            password = user_data.pop('password')
            user_data['password_hash'] = generate_password_hash(password)
            user = User(**user_data)
            session.add(user)
            users.append(user)

        session.commit()
        print("[INFO] Users seeded successfully")

        # Seed Courses
        courses_data = [
            {'name': 'Hiragana'},
            {'name': 'Katakana'},
            {'name': 'Kanji'}
        ]

        courses = []
        for course_data in courses_data:
            course = Course(**course_data)
            session.add(course)
            courses.append(course)

        session.commit()
        print("✓ Courses seeded successfully")

        # Seed Characters
        characters_data = [
            {'kana': 'あ', 'romaji': 'a', 'audio': 'hiragana_a.mp3', 'course_id': 1},
            {'kana': 'い', 'romaji': 'i', 'audio': 'hiragana_i.mp3', 'course_id': 1},
            {'kana': 'う', 'romaji': 'u', 'audio': 'hiragana_u.mp3', 'course_id': 1},
            {'kana': 'ア', 'romaji': 'a', 'audio': 'katakana_a.mp3', 'course_id': 2},
            {'kana': 'イ', 'romaji': 'i', 'audio': 'katakana_i.mp3', 'course_id': 2}
        ]

        characters = []
        for char_data in characters_data:
            character = Character(**char_data)
            session.add(character)
            characters.append(character)

        session.commit()
        print("[INFO] Characters seeded successfully")

        # Seed Pricing
        pricing_data = [
            {'price': 1999, 'course_id': 1},
            {'price': 1999, 'course_id': 2},
            {'price': 4999, 'course_id': 3}
        ]

        for price_data in pricing_data:
            pricing = Pricing(**price_data)
            session.add(pricing)

        session.commit()
        print("[INFO] Pricing seeded successfully")

        # Seed Transactions
        transactions_data = [
            {
                'user_id': 2,
                'course_id': 1,
                'card_number': '1234567890123456',
                'price': 1999
            },
            {
                'user_id': 3,
                'course_id': 2,
                'card_number': '9876543210987654',
                'price': 1999
            }
        ]

        transactions = []
        for trans_data in transactions_data:
            transaction = Transaction(**trans_data)
            session.add(transaction)
            transactions.append(transaction)

        session.commit()
        print("[INFO] Transactions seeded successfully")

        # Seed Enrollments
        enrollments_data = [
            {'user_id': 2, 'course_id': 1, 'transaction_id': 1},
            {'user_id': 3, 'course_id': 2, 'transaction_id': 2}
        ]

        for enroll_data in enrollments_data:
            enrollment = Enrollment(**enroll_data)
            session.add(enrollment)

        session.commit()
        print("[INFO] Enrollments seeded successfully")

        print("\n[INFO] Database seeded successfully!")

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] Error seeding database: {e}")
        raise
    finally:
        session.close()
