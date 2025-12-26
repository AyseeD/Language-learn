import argparse
from app.config import Config
from app import create_app
from app.database.seed import clear_database, seed_database

app = create_app()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='KanaLearn Flask Application')
    parser.add_argument('--clear', action='store_true', help='Clear the database before seeding')
    parser.add_argument('--seed', action='store_true', help='Seed the database with predefined information')
    args = parser.parse_args()

    if args.clear:
        clear_database()
    elif args.seed:
        seed_database()
    else:
        app.run(
            host=Config.HOST,
            port=Config.PORT,
            debug=Config.DEBUG,
        )

