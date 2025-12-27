import csv
from pathlib import Path
from sqlalchemy.orm import Session

from app import get_session
from app.database.models import Base, Role, User, Course, Character, Pricing


def initialize_database():
    # Create all tables if they don't exist
    print("[INFO] Initializing database...")
    try:
        from app import engine
        Base.metadata.create_all(bind=engine)
        print("  ✓ Database tables created/verified")
        return True
    except Exception as e:
        print(f"  ✗ Failed to initialize database: {e}")
        import traceback
        traceback.print_exc()
        return False


def load_characters_from_csv(csv_path='kana.csv'):
    # Load characters from CSV file and organize by course type

    # Get absolute path - this file is in app/database/seed.py
    base_dir = Path(__file__).resolve().parent  # app/database/
    full_csv_path = base_dir / csv_path

    print(f"[DEBUG] Looking for CSV at: {full_csv_path}")
    print(f"[DEBUG] File exists: {full_csv_path.exists()}")

    characters_by_course = {
        'Hiragana': [],
        'Katakana': [],
        'Kanji': []
    }

    if not full_csv_path.exists():
        print(f"[ERROR] CSV file not found at: {full_csv_path}")
        print(f"[INFO] Please ensure kana.csv is located in: {base_dir}")
        return characters_by_course

    try:
        with open(full_csv_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            headers = csv_reader.fieldnames

            print(f"[DEBUG] CSV Headers: {headers}")

            # Auto-detect column names (flexible for different CSV formats)
            type_col = next((h for h in headers if 'type' in h.lower() or 'category' in h.lower()), None)
            kana_col = next((h for h in headers if 'kana' in h.lower() or 'character' in h.lower()), None)
            romaji_col = next((h for h in headers if 'romaji' in h.lower() or 'roman' in h.lower()), None)

            if not all([type_col, kana_col, romaji_col]):
                print(f"[ERROR] Could not detect required columns")
                print(f"[ERROR] Found: type={type_col}, kana={kana_col}, romaji={romaji_col}")
                print(f"[INFO] CSV should have columns like: 'type', 'kana', 'romaji'")

                # Show first row as example
                file.seek(0)
                reader = csv.DictReader(file)
                first_row = next(reader, None)
                if first_row:
                    print(f"[DEBUG] First row: {first_row}")

                return characters_by_course

            print(f"[DEBUG] Using columns: {type_col} -> {kana_col} -> {romaji_col}")

            row_count = 0
            for row in csv_reader:
                row_count += 1

                course_type = row.get(type_col, '').strip()
                kana = row.get(kana_col, '').strip()
                romaji = row.get(romaji_col, '').strip()

                # Skip empty rows
                if not course_type or not kana or not romaji:
                    continue

                # Normalize course type (capitalize first letter)
                course_type = course_type.capitalize()

                if course_type in characters_by_course:
                    characters_by_course[course_type].append({
                        'kana': kana,
                        'romaji': romaji
                    })
                else:
                    # Try to map to known course types
                    if 'hira' in course_type.lower():
                        characters_by_course['Hiragana'].append({'kana': kana, 'romaji': romaji})
                    elif 'kata' in course_type.lower():
                        characters_by_course['Katakana'].append({'kana': kana, 'romaji': romaji})
                    elif 'kanji' in course_type.lower():
                        characters_by_course['Kanji'].append({'kana': kana, 'romaji': romaji})
                    else:
                        print(f"[WARNING] Row {row_count}: Unknown course type '{course_type}'")

            print(f"[INFO] Processed {row_count} rows from CSV")

        # Print summary
        total = 0
        for course, chars in characters_by_course.items():
            count = len(chars)
            total += count
            print(f"[DEBUG] {course}: {count} characters")
            if chars:
                # Show first 2 characters as example
                for char in chars[:2]:
                    print(f"  - {char['kana']} ({char['romaji']})")

        if total == 0:
            print(f"\n[WARNING] No characters were loaded!")
            print(f"[INFO] Please check your CSV format. Example format:")
            print(f"type,kana,romaji")
            print(f"Hiragana,あ,a")
            print(f"Hiragana,い,i")
            print(f"Katakana,ア,a")

    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")
        import traceback
        traceback.print_exc()

    return characters_by_course


def seed_roles(db: Session):
    # Seed roles table
    print("[INFO] Seeding roles...")

    roles_data = [
        {'code': 'ADMIN', 'name': 'Administrator'},
        {'code': 'USER', 'name': 'Regular User'},
        {'code': 'CUSTOMER', 'name': 'Customer'},
    ]

    for role_data in roles_data:
        existing = db.query(Role).filter_by(code=role_data['code']).first()
        if not existing:
            role = Role(**role_data)
            db.add(role)
            print(f"  ✓ Created role: {role_data['name']}")
        else:
            print(f"  - Role already exists: {role_data['name']}")

    db.commit()


def seed_courses_and_characters(db: Session):
    # Seed courses and their characters from CSV
    print("[INFO] Seeding courses and characters...")

    # Load characters from CSV
    characters_by_course = load_characters_from_csv('kana.csv')

    courses_data = [
        {'name': 'Hiragana', 'price': 1000},
        {'name': 'Katakana', 'price': 1000},
        {'name': 'Kanji', 'price': 2000},
    ]

    total_chars = 0

    for course_data in courses_data:
        course_name = course_data['name']

        # Create or get course
        course = db.query(Course).filter_by(name=course_name).first()
        if not course:
            course = Course(name=course_name)
            db.add(course)
            db.flush()  # Get the ID without committing
            print(f"  ✓ Created course: {course_name}")
        else:
            print(f"  - Course already exists: {course_name}")

        # Add pricing
        pricing = db.query(Pricing).filter_by(course_id=course.id).first()
        if not pricing:
            pricing = Pricing(course_id=course.id, price=course_data['price'])
            db.add(pricing)
            print(f"    ✓ Added pricing: ${course_data['price']}")

        # Add characters for this course
        characters = characters_by_course.get(course_name, [])
        char_count = 0

        for char_data in characters:
            # Check if character already exists
            existing = db.query(Character).filter_by(
                kana=char_data['kana'],
                course_id=course.id
            ).first()

            if not existing:
                character = Character(
                    kana=char_data['kana'],
                    romaji=char_data['romaji'],
                    course_id=course.id
                )
                db.add(character)
                char_count += 1

        if char_count > 0:
            print(f"    ✓ Added {char_count} characters")
        else:
            existing_count = db.query(Character).filter_by(course_id=course.id).count()
            print(f"    - Characters already exist: {existing_count}")

        total_chars += char_count

    db.commit()

    print(f"[INFO] Characters seeded successfully ({total_chars} new characters)")
    for course_name in ['Hiragana', 'Katakana', 'Kanji']:
        course = db.query(Course).filter_by(name=course_name).first()
        if course:
            count = db.query(Character).filter_by(course_id=course.id).count()
            print(f"  - {course_name}: {count} characters")


def seed_admin_user(db: Session):
    # Seed an admin user for testing
    print("[INFO] Seeding admin user...")

    admin = db.query(User).filter_by(username='admin').first()
    if not admin:
        admin_role = db.query(Role).filter_by(code='ADMIN').first()
        admin = User(
            name='Admin User',
            username='admin',
            password='admin123',  # Uses password setter with hashing
            role_code=admin_role.code if admin_role else None
        )
        db.add(admin)
        db.commit()
        print("  ✓ Created admin user (username: admin, password: admin123)")
    else:
        print("  - Admin user already exists")


def seed_demo_user(db: Session):
    # Seed a demo user for testing and enroll in Hiragana course
    print("[INFO] Seeding demo user...")

    demo_user = db.query(User).filter_by(username='johndoe').first()
    if not demo_user:
        role = db.query(Role).filter_by(code='CUSTOMER').first()
        demo_user = User(
            name='John Doe',
            username='johndoe',
            password='password',  # Uses password setter with hashing
            role_code=role.code if role else None
        )
        db.add(demo_user)
        db.flush()  # Get the user ID
        print("  ✓ Created demo user (username: johndoe, password: password)")
    else:
        print("  - Demo user already exists")

    # Enroll in Hiragana course
    hiragana_course = db.query(Course).filter_by(name='Hiragana').first()
    if hiragana_course:
        # Check if already enrolled
        from app.database.models import Enrollment, Transaction
        existing_enrollment = db.query(Enrollment).filter_by(
            user_id=demo_user.id,
            course_id=hiragana_course.id
        ).first()

        if not existing_enrollment:
            # Create a demo transaction
            pricing = db.query(Pricing).filter_by(course_id=hiragana_course.id).first()
            transaction = Transaction(
                user_id=demo_user.id,
                course_id=hiragana_course.id,
                card_number='4111111111111111',  # Demo card number
                price=pricing.price if pricing else 1000
            )
            db.add(transaction)
            db.flush()

            # Create enrollment
            enrollment = Enrollment(
                user_id=demo_user.id,
                course_id=hiragana_course.id,
                transaction_id=transaction.id
            )
            db.add(enrollment)
            db.commit()
            print(f"  ✓ Enrolled demo user in Hiragana course")
        else:
            print(f"  - Demo user already enrolled in Hiragana course")
    else:
        print(f"  ⚠️  Hiragana course not found - skipping enrollment")


def seed_database():
    # Main seeding function
    print("\n" + "=" * 60)
    print("DATABASE SEEDING")
    print("=" * 60 + "\n")

    # Initialize database first
    if not initialize_database():
        print("\n❌ DATABASE INITIALIZATION FAILED")
        print("Cannot proceed with seeding.")
        return

    try:
        with get_session() as db:
            # Seed in order (respecting foreign keys)
            seed_roles(db)
            seed_courses_and_characters(db)
            seed_admin_user(db)
            seed_demo_user(db)

            print("\n" + "=" * 60)
            print("✅ DATABASE SEEDING COMPLETED SUCCESSFULLY")
            print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR during seeding: {e}")
        import traceback
        traceback.print_exc()


def clear_database():
    # Clear all data from database (use with caution!)
    print("\n" + "=" * 60)
    print("⚠️  DATABASE CLEARING")
    print("=" * 60 + "\n")

    confirmation = input("Are you sure you want to clear the database? Type 'YES' to confirm: ")

    if confirmation != 'YES':
        print("Aborted.")
        return

    try:
        with get_session() as db:
            # Delete in reverse order of foreign key dependencies
            print("[INFO] Clearing Progress...")
            from app.database.models import Progress
            db.query(Progress).delete()

            print("[INFO] Clearing Enrollments...")
            from app.database.models import Enrollment
            db.query(Enrollment).delete()

            print("[INFO] Clearing Transactions...")
            from app.database.models import Transaction
            db.query(Transaction).delete()

            print("[INFO] Clearing Characters...")
            db.query(Character).delete()

            print("[INFO] Clearing Pricing...")
            db.query(Pricing).delete()

            print("[INFO] Clearing Courses...")
            db.query(Course).delete()

            print("[INFO] Clearing Users...")
            db.query(User).delete()

            print("[INFO] Clearing Roles...")
            db.query(Role).delete()

            db.commit()

            print("\n" + "=" * 60)
            print("✅ DATABASE CLEARED SUCCESSFULLY")
            print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR during clearing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # For testing this script directly
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'clear':
        clear_database()
    else:
        seed_database()